import assert from "node:assert";
import test from "node:test";

process.env.SESSION_SECRET = "unit-test-secret";

const { makeToken, verifyToken } = await import("../lib/session.ts");

const DAY = 24 * 60 * 60 * 1000;
const now = 1_700_000_000_000;

test("a fresh token verifies", () => {
  assert.equal(verifyToken(makeToken(now)!, now), true);
  assert.equal(verifyToken(makeToken(now - 6 * DAY)!, now), true);
});

test("a token older than 7 days is rejected", () => {
  assert.equal(verifyToken(makeToken(now - 8 * DAY)!, now), false);
});

test("a tampered MAC is rejected", () => {
  const t = makeToken(now)!;
  assert.equal(verifyToken(t.slice(0, -1) + (t.endsWith("a") ? "b" : "a"), now), false);
});

test("a tampered issued-at (re-dated to look fresh) is rejected", () => {
  const t = makeToken(now - 30 * DAY)!;
  const forged = `${now}.${t.split(".")[1]}`; // new iat, old MAC
  assert.equal(verifyToken(forged, now), false);
});

test("a future-dated token is rejected", () => {
  assert.equal(verifyToken(makeToken(now + 10 * 60 * 1000)!, now), false);
});

test("garbage and empty are rejected", () => {
  assert.equal(verifyToken("", now), false);
  assert.equal(verifyToken("nonsense", now), false);
  assert.equal(verifyToken(undefined, now), false);
});
