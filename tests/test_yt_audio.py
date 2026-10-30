import unittest
import os
import socket
import tempfile
from pathlib import Path
from unittest import mock

import index


class MediaUrlTests(unittest.TestCase):
    def test_keeps_http_url(self):
        url = "https://www.youtube.com/watch?v=example"
        self.assertEqual(index.media_url(url), url)

    def test_converts_search_to_youtube_search(self):
        self.assertEqual(index.media_url("lofi radio"), "ytsearch1:lofi radio")

    def test_rejects_empty_query(self):
        with self.assertRaises(index.PlayerError):
            index.media_url("  ")


class YoutubeUrlTests(unittest.TestCase):
    def test_accepts_youtube_hosts(self):
        self.assertTrue(index.is_youtube_url("https://www.youtube.com/watch?v=example"))
        self.assertTrue(index.is_youtube_url("https://youtu.be/example"))

    def test_rejects_non_youtube_hosts(self):
        self.assertFalse(index.is_youtube_url("https://youtube.com.example.org/watch?v=example"))
        self.assertFalse(index.is_youtube_url("file:///tmp/video"))


class PlayerControlTests(unittest.TestCase):
    def test_pip_requests_video_and_audio_formats(self):
        with tempfile.TemporaryDirectory() as runtime_dir:
            path = Path(runtime_dir) / index.SOCKET_NAME
            server = socket.socket(socket.AF_UNIX)

            def start_mpv(arguments, **kwargs):
                socket_argument = next(
                    argument
                    for argument in arguments
                    if argument.startswith("--input-ipc-server=")
                )
                server.bind(socket_argument.split("=", 1)[1])
                return mock.Mock(poll=lambda: None)

            with (
                mock.patch.object(index, "socket_path", return_value=path),
                mock.patch.object(index.shutil, "which", side_effect=["/usr/bin/mpv", "/usr/bin/yt-dlp"]),
                mock.patch.object(index.subprocess, "Popen", side_effect=start_mpv) as popen,
                mock.patch.object(index, "ipc", return_value={"data": True}),
            ):
                try:
                    index.start_player(
                        "https://www.youtube.com/watch?v=example",
                        pip=True,
                        ipc_path=path,
                    )
                finally:
                    server.close()

        arguments = popen.call_args.args[0]
        self.assertIn(
            "--ytdl-format=bestvideo[height<=720]+bestaudio/best[height<=720]",
            arguments,
        )

    def test_play_can_replace_active_track(self):
        with tempfile.TemporaryDirectory() as runtime_dir:
            path = Path(runtime_dir) / index.SOCKET_NAME
            server = socket.socket(socket.AF_UNIX)
            server.bind(str(path))
            try:
                with (
                    mock.patch.object(index, "socket_path", return_value=path),
                    mock.patch.object(index, "ipc", return_value={"data": False}) as ipc,
                    mock.patch.object(index, "start_player") as start_player,
                ):
                    index.play(
                        "https://youtu.be/example",
                        pip=False,
                        replace_active=True,
                    )
            finally:
                server.close()

        ipc.assert_has_calls(
            [
                mock.call(["get_property", "pause"], missing_ok=True),
                mock.call(["loadfile", "https://youtu.be/example", "replace"]),
            ]
        )
        start_player.assert_not_called()

    def test_seek_uses_exact_relative_offset(self):
        with mock.patch.object(index, "ipc") as ipc:
            index.seek(-30)

        ipc.assert_called_once_with(["seek", -30, "relative+exact"])

    def test_pip_position_uses_playback_time_when_time_pos_is_unavailable(self):
        with mock.patch.object(
            index,
            "ipc",
            side_effect=[{"data": None}, {"data": 18.25}],
        ) as ipc:
            position = index._playback_position(Path("/tmp/mpv.sock"))

        self.assertEqual(position, 18.25)
        self.assertEqual(
            [call.args[0] for call in ipc.call_args_list],
            [
                ["get_property", "time-pos"],
                ["get_property", "playback-time"],
            ],
        )

    def test_pip_waits_for_a_selected_video_track(self):
        ipc_path = Path("/tmp/mpv-pip.sock")
        with (
            mock.patch.object(
                index,
                "ipc",
                side_effect=[
                    {"data": "auto"},
                    {"data": "auto"},
                    {"data": 2},
                ],
            ) as ipc,
            mock.patch.object(index.time, "sleep"),
            mock.patch.object(index, "START_TIMEOUT", 1),
        ):
            index._wait_for_video(ipc_path)

        self.assertEqual(ipc.call_count, 3)
        self.assertTrue(
            all(call.args[0] == ["get_property", "vid"] for call in ipc.call_args_list)
        )

    def test_pip_switch_preserves_source_and_position(self):
        with tempfile.TemporaryDirectory() as runtime_dir:
            path = Path(runtime_dir) / index.SOCKET_NAME
            server = socket.socket(socket.AF_UNIX)
            server.bind(str(path))
            server.close()
            pip_server = socket.socket(socket.AF_UNIX)
            commands = []

            def ipc_response(command, *, missing_ok=False, ipc_path=None):
                commands.append((command, ipc_path))
                if ipc_path == path and command == ["get_property", "pause"]:
                    return None
                if command == ["get_property", "time-pos"]:
                    return {"data": 42.5}
                if command == ["get_property", "vid"]:
                    return {"data": 1}
                return {"error": "success"}

            def start_pip_player(*args, ipc_path, **kwargs):
                pip_server.bind(str(ipc_path))
                pip_server.listen(1)

            with (
                mock.patch.object(index, "socket_path", return_value=path),
                mock.patch.object(
                    index,
                    "get_property",
                    side_effect=["https://www.youtube.com/watch?v=example", True],
                ),
                mock.patch.object(index, "ipc", side_effect=ipc_response),
                mock.patch.object(index, "start_player", side_effect=start_pip_player) as start_player,
            ):
                try:
                    index.switch_to_pip()
                finally:
                    pip_server.close()

            pip_path = start_player.call_args.kwargs["ipc_path"]
            self.assertEqual(
                [command for command, _ in commands],
                [
                    ["get_property", "time-pos"],
                    ["get_property", "vid"],
                    ["quit"],
                    ["get_property", "pause"],
                ],
            )
            self.assertIs(commands[0][1], path)
            self.assertIs(commands[1][1], pip_path)
            self.assertIs(commands[2][1], path)
            self.assertIs(commands[3][1], path)
            self.assertTrue(path.is_socket())
            self.assertEqual(start_player.call_args.args[0], "https://www.youtube.com/watch?v=example")
            self.assertEqual(start_player.call_args.kwargs["pip"], True)
            self.assertEqual(start_player.call_args.kwargs["start_time"], 42.5)
            self.assertEqual(start_player.call_args.kwargs["paused"], True)
            self.assertTrue(str(pip_path).startswith(str(path) + ".pip-"))

    def test_pip_switch_keeps_audio_when_video_has_no_track(self):
        with tempfile.TemporaryDirectory() as runtime_dir:
            path = Path(runtime_dir) / index.SOCKET_NAME
            server = socket.socket(socket.AF_UNIX)
            server.bind(str(path))
            server.close()
            pip_server = socket.socket(socket.AF_UNIX)

            def ipc_response(command, *, missing_ok=False, ipc_path=None):
                if ipc_path == path:
                    if command == ["get_property", "time-pos"]:
                        return {"data": 12.0}
                    if command == ["get_property", "pause"]:
                        return {"data": False}
                if command == ["get_property", "vid"]:
                    return {"data": None}
                if command == ["get_property", "pause"]:
                    return None
                return {"error": "success"}

            def start_pip_player(*args, ipc_path, **kwargs):
                pip_server.bind(str(ipc_path))
                pip_server.listen(1)

            with (
                mock.patch.object(index, "socket_path", return_value=path),
                mock.patch.object(
                    index,
                    "get_property",
                    side_effect=["https://www.youtube.com/watch?v=example", False],
                ),
                mock.patch.object(index, "ipc", side_effect=ipc_response) as ipc,
                mock.patch.object(index, "start_player", side_effect=start_pip_player),
                mock.patch.object(index, "START_TIMEOUT", 0.01),
            ):
                try:
                    with self.assertRaisesRegex(index.PlayerError, "lecture audio en cours a été conservée"):
                        index.switch_to_pip()
                finally:
                    pip_server.close()

            self.assertTrue(path.is_socket())
            self.assertFalse(
                any(
                    call.args[0] == ["quit"] and call.kwargs.get("ipc_path") == path
                    for call in ipc.call_args_list
                )
            )

    def test_pip_switch_rejects_non_youtube_media(self):
        with tempfile.TemporaryDirectory() as runtime_dir:
            path = Path(runtime_dir) / index.SOCKET_NAME
            path.touch()
            with (
                mock.patch.object(index, "socket_path", return_value=path),
                mock.patch.object(index, "get_property", return_value="https://example.org/video"),
                mock.patch.object(index, "ipc") as ipc,
            ):
                with self.assertRaises(index.PlayerError):
                    index.switch_to_pip()

        ipc.assert_not_called()


class StatusTests(unittest.TestCase):
    def test_stale_ipc_socket_is_reported_as_stopped(self):
        with tempfile.TemporaryDirectory() as runtime_dir:
            path = os.path.join(runtime_dir, index.SOCKET_NAME)
            server = socket.socket(socket.AF_UNIX)
            server.bind(path)
            server.close()
            previous_runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
            os.environ["XDG_RUNTIME_DIR"] = runtime_dir
            try:
                self.assertEqual(index.status()["class"], "stopped")
            finally:
                if previous_runtime_dir is None:
                    os.environ.pop("XDG_RUNTIME_DIR", None)
                else:
                    os.environ["XDG_RUNTIME_DIR"] = previous_runtime_dir



if __name__ == "__main__":
    unittest.main()
