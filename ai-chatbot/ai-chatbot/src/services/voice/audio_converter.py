import io
import struct
import wave

class AudioConverter:

    @staticmethod
    def pcm_to_wav(
        pcm_data: bytes,
        sample_rate: int = 8000,
        channels: int = 1,
        sample_width: int = 2,
    ) -> bytes:

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)
        return buf.getvalue()

    @staticmethod
    def resample(pcm_data: bytes, from_rate: int, to_rate: int) -> bytes:

        if from_rate == to_rate or not pcm_data:
            return pcm_data

        n_samples = len(pcm_data) // 2
        if n_samples == 0:
            return b""

        samples = struct.unpack(f"<{n_samples}h", pcm_data)
        ratio = from_rate / to_rate
        out_len = int(n_samples / ratio)
        result = []

        for i in range(out_len):
            src_pos = i * ratio
            idx = int(src_pos)
            frac = src_pos - idx
            if idx + 1 < n_samples:
                val = samples[idx] * (1.0 - frac) + samples[idx + 1] * frac
            elif idx < n_samples:
                val = float(samples[idx])
            else:
                val = 0.0
            result.append(int(max(-32768, min(32767, val))))

        return struct.pack(f"<{len(result)}h", *result)

    @staticmethod
    def resample_24k_to_8k(pcm_24k: bytes) -> bytes:

        n_samples = len(pcm_24k) // 2
        if n_samples < 3:
            return b""

        samples = struct.unpack(f"<{n_samples}h", pcm_24k)
        result = []
        for i in range(0, n_samples - 2, 3):
            avg = (samples[i] + samples[i + 1] + samples[i + 2]) // 3
            result.append(max(-32768, min(32767, avg)))

        return struct.pack(f"<{len(result)}h", *result)

    @staticmethod
    def resample_8k_to_16k(pcm_8k: bytes) -> bytes:

        n_samples = len(pcm_8k) // 2
        if n_samples == 0:
            return b""

        samples = struct.unpack(f"<{n_samples}h", pcm_8k)
        result = []
        for i in range(n_samples - 1):
            result.append(samples[i])
            mid = (samples[i] + samples[i + 1]) // 2
            result.append(mid)

        result.append(samples[-1])
        result.append(samples[-1])

        return struct.pack(f"<{len(result)}h", *result)
