from io import BytesIO

import av

from app.modules.portfolio.deadline import Deadline
from app.modules.portfolio.errors import (
    Rejected,
    rejected_invalid,
    rejected_limit,
    rejected_media,
)
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


def packet_end(packet: "av.Packet[av.VideoStream]") -> float | None:
    """End stamp of a demuxed packet in seconds, or None when it carries no timestamp."""
    stamp = packet.pts if packet.pts is not None else packet.dts
    if stamp is None or packet.time_base is None:
        return None
    return float((stamp + (packet.duration or 0)) * packet.time_base)


def check_declared(container: av.container.InputContainer) -> None:
    """Cheap first pass on the header; never the last word (see demuxed_seconds)."""
    if container.duration is None:
        raise rejected_invalid("VIDEO_DURATION")
    seconds = container.duration / av.time_base
    if seconds <= 0 or seconds > MAX_VIDEO_SECONDS:
        raise rejected_invalid("VIDEO_DURATION")


def demuxed_seconds(
    container: av.container.InputContainer, stream: av.VideoStream, deadline: Deadline
) -> float:
    """Walks packet timestamps only: nothing is decoded and no packet is retained.

    A header claiming a short duration cannot hide longer content: the walk rejects as
    soon as the real stamps pass the ceiling. If the packet budget runs out first the
    real duration stays unbounded, so the file is refused rather than trusted.
    """
    seconds = 0.0
    for index, packet in enumerate(container.demux(stream)):
        if index % 200 == 0:
            deadline.check()
        end = packet_end(packet)
        if end is not None:
            seconds = max(seconds, end)
        if seconds > MAX_VIDEO_SECONDS:
            raise rejected_invalid("VIDEO_DURATION")
        if index >= MAX_PACKETS:
            raise rejected_limit()
    return seconds


def inspect(data: bytes, deadline: Deadline) -> None:
    """Container parse and bounded demux; no transcoding and no temporary file."""
    deadline.check()
    try:
        with av.open(BytesIO(data), "r") as container:
            if "mp4" not in container.format.name.split(","):
                raise rejected_media()
            stream = check_streams(container)
            check_declared(container)
            if demuxed_seconds(container, stream, deadline) <= 0:
                raise rejected_invalid("VIDEO_DURATION")
    except Rejected:
        raise
    except (av.FFmpegError, OSError, ValueError, StopIteration):
        raise rejected_invalid("VIDEO_UNREADABLE") from None
