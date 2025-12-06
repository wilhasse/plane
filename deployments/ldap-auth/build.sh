#!/bin/bash
#
# Build custom Plane images with LDAP authentication
#
# Usage:
#   ./build.sh                    # Build with 'stable' tag
#   ./build.sh v0.23.0            # Build with specific Plane version
#   ./build.sh stable myregistry  # Build and tag for custom registry
#

set -e

PLANE_VERSION="${1:-stable}"
REGISTRY="${2:-}"
TAG="${REGISTRY:+$REGISTRY/}plane-api-ldap:${PLANE_VERSION}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Building Plane API with LDAP ==="
echo "Base version: $PLANE_VERSION"
echo "Image tag: $TAG"
echo ""

docker build \
    --build-arg PLANE_VERSION="$PLANE_VERSION" \
    -f Dockerfile.api \
    -t "$TAG" \
    .

echo ""
echo "=== Build Complete ==="
echo "Image: $TAG"
echo ""
echo "To use this image, update docker-compose.ldap.yml:"
echo ""
echo "  api:"
echo "    image: $TAG"
echo "  worker:"
echo "    image: $TAG"
echo "  beat-worker:"
echo "    image: $TAG"
echo "  migrator:"
echo "    image: $TAG"
echo ""

if [ -n "$REGISTRY" ]; then
    echo "To push to registry:"
    echo "  docker push $TAG"
fi
