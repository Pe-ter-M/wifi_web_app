#!/bin/bash
# RADIUS auth test script — runs inside the Docker network
# Usage: docker compose exec freeradius bash /tmp/test_auth.sh
# Or:  ./test_auth.sh --local (if radclient is installed on host)

set -e

RADIUS_HOST="${1:-freeradius}"
RADIUS_SECRET="testing123"
RADIUS_PORT="1812"

echo "=== RADIUS Auth Test Suite ==="
echo "Target: $RADIUS_HOST:$RADIUS_PORT"
echo ""

# Test 1: Active user should get Access-Accept
echo "--- Test 1: Active user 'test_active' should AUTHENTICATE ---"
if echo "User-Name=test_active, User-Password=testpass123" \
    | radclient -x "$RADIUS_HOST:$RADIUS_PORT" auth "$RADIUS_SECRET" 2>&1 \
    | grep -q "Access-Accept"
then
    echo "  ✓ PASS: Active user authenticated"
else
    echo "  ✗ FAIL: Active user was rejected"
fi
echo ""

# Test 2: Expired user should get Access-Reject
echo "--- Test 2: Expired user 'test_expired' should be REJECTED ---"
if echo "User-Name=test_expired, User-Password=expired123" \
    | radclient -x "$RADIUS_HOST:$RADIUS_PORT" auth "$RADIUS_SECRET" 2>&1 \
    | grep -q "Access-Reject"
then
    echo "  ✓ PASS: Expired user rejected"
else
    echo "  ✗ FAIL: Expired user was accepted"
fi
echo ""

# Test 3: Wrong password should always be rejected
echo "--- Test 3: Wrong password should be REJECTED ---"
if echo "User-Name=test_active, User-Password=wrongpass" \
    | radclient -x "$RADIUS_HOST:$RADIUS_PORT" auth "$RADIUS_SECRET" 2>&1 \
    | grep -q "Access-Reject"
then
    echo "  ✓ PASS: Wrong password rejected"
else
    echo "  ✗ FAIL: Wrong password was accepted"
fi
echo ""

# Test 4: Nonexistent user should be rejected
echo "--- Test 4: Unknown user should be REJECTED ---"
if echo "User-Name=nobody, User-Password=nopass" \
    | radclient -x "$RADIUS_HOST:$RADIUS_PORT" auth "$RADIUS_SECRET" 2>&1 \
    | grep -q "Access-Reject"
then
    echo "  ✓ PASS: Unknown user rejected"
else
    echo "  ✗ FAIL: Unknown user was accepted"
fi
echo ""

echo "=== All tests completed ==="
