#!/bin/bash
# New look for all three papers (A and C re-rendered from saved content, B re-run), then gallery, push, redeploy.
cd /c/Users/ankit/hacktober-2026/steer/ps2
export PYTHONIOENCODING=utf-8
rm -rf out/_preview
.venv/Scripts/python rerender.py out/wilding-et-al-diabetes-obes-metab-2022 || echo "FAILED A"
.venv/Scripts/python rerender.py out/mclaren-et-al-nat-metab-2024 || echo "FAILED C"
.venv/Scripts/python run.py PMC11611443 2>&1 | grep -v fontTools || echo "FAILED B"
.venv/Scripts/python gallery.py || echo "FAILED gallery"
git add -A
git -c user.name=Ankith-m1006 -c user.email=22bsm006@iiitdmj.ac.in commit -q -m "Doctor's-note design (Fraunces, Manrope, Kalam), downloads and a ZIP per paper; re-render all three papers

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_013TFnY5wjFDuFmXvcZLRvrU"
git push -q || echo "FAILED push"
cd ../ps2-deploy && rm -rf site && mkdir site && cp ../ps2/out/index.html site/
for d in ../ps2/out/*/; do n=$(basename "$d"); mkdir -p "site/$n"; cp -r "$d/carousel" "$d/reel_frames" "site/$n/"; cp "$d"/static.png "$d"/static_square.png "$d"/reel_*.mp4 "$d"/review.html "$d"/caption.txt "$d"/posts.zip "site/$n/"; done
/c/Users/ankit/tools/google-cloud-sdk/bin/gcloud.cmd run deploy steer-paper-to-posts --source . --region asia-south1 --allow-unauthenticated --quiet 2>&1 | tail -n 2
echo REDO_ALL_DONE
