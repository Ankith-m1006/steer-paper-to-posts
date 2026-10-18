"""Create: a 9:16 reel from the scenes. AI voiceover (Microsoft neural voices through edge-tts,
Indian English or Hindi), slow-zoom motion on each frame, and burned-in subtitles, joined with ffmpeg."""
import asyncio
import json
import pathlib
import subprocess

import edge_tts

VOICES = {"en": "en-IN-NeerjaNeural", "hi": "hi-IN-SwaraNeural"}
FPS = 30


async def _speak(text, voice, path):
    await edge_tts.Communicate(text, voice, rate="+4%").save(str(path))


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


def _srt_time(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"


def _chunks(text, n=6):
    words = text.split()
    return [" ".join(words[i:i + n]) for i in range(0, len(words), n)]


def build(scenes, frames, out_dir, lang="en", lines_key="voice"):
    out = pathlib.Path(out_dir)
    work = out / f"reel_work_{lang}"
    work.mkdir(parents=True, exist_ok=True)
    srt, t, clips, audios = [], 0.0, [], []
    for i, (scene, frame) in enumerate(zip(scenes, frames), 1):
        audio = work / f"vo_{i:02d}.mp3"
        asyncio.run(_speak(scene[lines_key], VOICES[lang], audio))
        dur = duration(audio) + 0.35
        # Subtitles: the spoken line in short chunks, spread evenly over the scene.
        parts = _chunks(scene[lines_key])
        for k, p in enumerate(parts):
            a, b = t + dur * k / len(parts), t + dur * (k + 1) / len(parts) - 0.05
            srt.append(f"{len(srt) + 1}\n{_srt_time(a)} --> {_srt_time(b)}\n{p}\n")
        clip = work / f"clip_{i:02d}.mp4"
        frames_n = int(dur * FPS)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", str(frame), "-i", str(audio),
                        "-filter_complex",
                        f"[0]scale=1188:2112,zoompan=z='min(zoom+0.0006,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                        f"d={frames_n}:s=1080x1920:fps={FPS},fade=t=in:st=0:d=0.25,fade=t=out:st={dur - 0.25:.2f}:d=0.25[v];"
                        f"[1]apad=pad_dur=0.35[a]",
                        "-map", "[v]", "-map", "[a]", "-t", f"{dur:.2f}", "-c:v", "libx264", "-preset", "veryfast",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", str(clip)], check=True)
        clips.append(clip)
        t += dur
    (work / "subs.srt").write_text("\n".join(srt), encoding="utf-8")
    (work / "list.txt").write_text("".join(f"file '{c.name}'\n" for c in clips), encoding="utf-8")
    joined = work / "joined.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "joined.mp4"],
                   cwd=work, check=True)
    final = out / f"reel_{lang}.mp4"
    # Brand fonts for the subtitles (Manrope, Mukta for Hindi): copy them next to the subtitles so ffmpeg's libass can load it by name.
    for f in (pathlib.Path(__file__).resolve().parents[1] / "fonts").glob("*.ttf"):
        if f.name.startswith(("Manrope", "Mukta")):
            (work / f.name).write_bytes(f.read_bytes())
    face = "Mukta" if lang == "hi" else "Manrope"
    style = (f"FontName={face},FontSize=12,Bold=0,PrimaryColour=&H00EBF2F8,OutlineColour=&H00141466,BackColour=&H00141466,"
             "BorderStyle=3,Outline=5,Shadow=0,MarginV=78,MarginL=30,MarginR=30,Alignment=2")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "joined.mp4", "-vf", f"subtitles=subs.srt:fontsdir=.:force_style='{style}'",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "copy",
                    "-movflags", "+faststart", str(final.resolve())], cwd=work, check=True)
    return str(final), round(t, 1)
