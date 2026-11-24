#!/bin/sh
# Fetches the model's GGUF file from Docker Hub's ai/ namespace into MODEL_DIR, once per
# MODEL_DIGEST, and checks it against that digest before llama-server may load it.
#
# llama-server's own --docker-repo download is not used: in llama.cpp 1.0 it fails after a
# successful download ("invalid URL: no scheme"), and it cannot read the CNCF ModelPack layers
# that Docker Hub's newer ai/ tags use. A blob fetched by its digest works for either kind.
set -eu

model="$MODEL_DIR/model.gguf"
if [ -s "$model" ] && [ "$(cat "$MODEL_DIR/model.digest" 2>/dev/null)" = "$MODEL_DIGEST" ]; then
    echo "Model $MODEL_DIGEST is already present"
    exit 0
fi

token=$(curl -fsS "https://auth.docker.io/token?service=registry.docker.io&scope=repository:$MODEL_REPOSITORY:pull" \
    | sed -n 's/.*"token": *"\([^"]*\)".*/\1/p')

echo "Fetching $MODEL_REPOSITORY@$MODEL_DIGEST"
# -C - resumes a download a restart interrupted; a partial file from another digest fails the
# check below and is removed, so the next attempt starts clean.
curl -fSL --no-progress-meter --retry 5 --retry-all-errors -C - -o "$model.partial" \
    -H "Authorization: Bearer $token" \
    "https://registry-1.docker.io/v2/$MODEL_REPOSITORY/blobs/$MODEL_DIGEST"

if ! echo "${MODEL_DIGEST#sha256:}  $model.partial" | sha256sum -c -; then
    rm -f "$model.partial"
    exit 1
fi
mv "$model.partial" "$model"
echo "$MODEL_DIGEST" > "$MODEL_DIR/model.digest"
