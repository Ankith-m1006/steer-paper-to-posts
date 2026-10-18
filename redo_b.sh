#!/bin/bash
# Rerun paper B with the label fix, rebuild the gallery, push, and redeploy the gallery.
set -e
cd /c/Users/ankit/hacktober-2026/steer/ps2
export PYTHONIOENCODING=utf-8
.venv/Scripts/python run.py PMC11611443 2>&1 | grep -v fontTools
.venv/Scripts/python gallery.py
git add -A
git -c user.name=Ankith-m1006 -c user.email=22bsm006@iiitdmj.ac.in commit -q -m "Treat labels like STEP-1 as names, not numbers, in the claim verifier; rerun the muscle paper

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_013TFnY5wjFDuFmXvcZLRvrU"
git push -q
cd ../ps2-deploy && rm -rf site && mkdir site && cp ../ps2/out/index.html site/
for d in ../ps2/out/*/; do n=$(basename "$d"); mkdir -p "site/$n"; cp -r "$d/carousel" "$d/reel_frames" "site/$n/"; cp "$d"/static.png "$d"/static_square.png "$d"/reel_*.mp4 "$d"/review.html "$d"/caption.txt "site/$n/"; done
/c/Users/ankit/tools/google-cloud-sdk/bin/gcloud.cmd run deploy steer-paper-to-posts --source . --region asia-south1 --allow-unauthenticated --quiet 2>&1 | tail -n 2
echo REDO_DONE
