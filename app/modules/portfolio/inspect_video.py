from io import BytesIO

import av

from app.modules.portfolio.deadline import Deadline
from app.modules.portfolio.errors import Rejected, rejected_invalid, rejected_media
from app.modules.portfolio.limits import MAX_VIDEO_SECONDS, resolution_allowed

MAX_PACKETS = 20000


def check_streams(container: av.container.InputContainer) -> av.VideoStream:
    video = [stream for stream in container.streams if stream.type == "video"]
    audio = [stream for stream in container.streams if stream.type == "audio"]
    if len(video) != 1 or len(video) + len(audio) != len(container.streams):
        raise rejected_media()
    stream = video[0]
    if not isinstance(stream, av.VideoStream) or stream.codec_context.name != "h264":
        raise rejected_media()
    if any(item.codec_context.name != "aac" for item in audio):
        raise rejected_media()
    width, height = stream.codec_context.width, stream.codec_context.height
    if width < 1 or height < 1 or not resolution_allowed(width, height):
        raise rejected_invalid("VIDEO_RESOLUTION")
    return stream


def check_duration(container: av.container.InputContainer) -> None:
    if container.duration is None:
        raise rejected_invalid("VIDEO_DURATION")
    seconds = container.duration / av.time_base
    if seconds <= 0 or seconds > MAX_VIDEO_SECONDS:
        raise rejected_invalid("VIDEO_DURATION")


def inspect(data: bytes, deadline: Deadline) -> None:
    """Container parse and bounded demux; no transcoding and no temporary file."""
    deadline.check()
    try:
        with av.open(BytesIO(data), "r") as container:
            if "mp4" not in container.format.name.split(","):
                raise rejected_media()
            stream = check_streams(container)
            check_duration(container)
            for index, _ in enumerate(container.demux(stream)):
                if index % 200 == 0:
                    deadline.check()
                if index >= MAX_PACKETS:
                    break
    except Rejected:
        raise
    except (av.FFmpegError, OSError, ValueError, StopIteration):
        raise rejected_invalid("VIDEO_UNREADABLE") from None
