import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { loginSchema } from "./login-schema.ts";

describe("loginSchema", () => {
  it("accepts demo credentials", () => {
    const parsed = loginSchema.parse({
      email: "admin@twinpilot.demo",
      password: "TwinPilot-Admin-Demo!",
    });
    assert.equal(parsed.email, "admin@twinpilot.demo");
  });

  it("rejects short passwords", () => {
    const result = loginSchema.safeParse({
      email: "admin@twinpilot.demo",
      password: "short",
    });
    assert.equal(result.success, false);
  });

  it("rejects invalid email", () => {
    const result = loginSchema.safeParse({
      email: "not-an-email",
      password: "TwinPilot-Admin-Demo!",
    });
    assert.equal(result.success, false);
  });
});
