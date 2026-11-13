from io import BytesIO

import av

WIDTH, HEIGHT, RATE, SAMPLE_RATE = 64, 48, 10, 44100


def encode_video(
    container: av.container.OutputContainer, stream: av.VideoStream, frames: int
) -> None:
    width, height = stream.width, stream.height
    for index in range(frames):
        frame = av.VideoFrame(width, height, "yuv420p")
        for plane in frame.planes:
            plane.update(bytes(plane.buffer_size))
        frame.pts = index
        for packet in stream.encode(frame):
            container.mux(packet)
    for packet in stream.encode():
        container.mux(packet)


def encode_audio(
    container: av.container.OutputContainer, stream: av.AudioStream
) -> None:
    frame = av.AudioFrame(format="fltp", layout="stereo", samples=1024)
    for plane in frame.planes:
        plane.update(bytes(plane.buffer_size))
    frame.sample_rate, frame.pts = SAMPLE_RATE, 0
    for packet in stream.encode(frame):
        container.mux(packet)
    for packet in stream.encode():
        container.mux(packet)


def mp4_bytes(
    frames: int = 10,
    width: int = WIDTH,
    height: int = HEIGHT,
    codec: str = "libx264",
    audio: str | None = None,
    container_format: str = "mp4",
) -> bytes:
    """Every stream is declared before muxing starts, as the MP4 muxer requires."""
    buffer = BytesIO()
    with av.open(buffer, "w", format=container_format) as container:
        video = container.add_stream(codec, rate=RATE)
        video.width, video.height, video.pix_fmt = width, height, "yuv420p"
        sound = None if audio is None else container.add_stream(audio, rate=SAMPLE_RATE)
        if sound is not None:
            sound.layout = "stereo"
        encode_video(container, video, frames)
        if sound is not None:
            encode_audio(container, sound)
    return buffer.getvalue()


def box_timescale(data: bytearray, box: bytes) -> tuple[int, int]:
    """Offset of an MP4 header box and the timescale it declares (version 0 layout)."""
    index = data.find(box)
    if index < 0:
        raise ValueError(f"{box.decode()} box absent")
    return index, int.from_bytes(data[index + 16 : index + 20], "big")


def lying_mp4_bytes(frames: int, declared_seconds: float) -> bytes:
    """An honest stream under a header rewritten to claim a shorter duration.

    mvhd, mdhd and tkhd carry the declared durations; the sample tables that drive the
    packet timestamps are untouched, so the file holds `frames` worth of real content.
    """
    data = bytearray(mp4_bytes(frames=frames))
    movie, movie_scale = box_timescale(data, b"mvhd")
    media, media_scale = box_timescale(data, b"mdhd")
    track, _ = box_timescale(data, b"tkhd")
    headers = ((movie + 20, movie_scale), (media + 20, media_scale), (track + 24, movie_scale))
    for offset, scale in headers:
        data[offset : offset + 4] = int(declared_seconds * scale).to_bytes(4, "big")
    return bytes(data)
