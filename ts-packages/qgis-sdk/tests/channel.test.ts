/**
 * One QWebChannel per transport. Qt's QWebChannel takes over `transport.onmessage` when it is
 * constructed, so a second channel on the same page silently stops the first one's replies.
 * These tests stand in a counting fake for the constructor.
 */

import { describe, expect, it } from "bun:test";

import { openChannel } from "@/channel.ts";

function countingChannel() {
	const built: object[] = [];
	class FakeChannel {
		objects = { bridge: { name: "bridge" } };
		constructor(_transport: unknown, onInit: (channel: unknown) => void) {
			built.push(this);
			queueMicrotask(() => onInit(this));
		}
	}
	return {
		built,
		Ctor: FakeChannel as unknown as new (
			transport: unknown,
			onInit: (channel: unknown) => void,
		) => unknown,
	};
}

const tick = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("openChannel", () => {
	it("builds one channel per transport and hands it to every caller", async () => {
		const { built, Ctor } = countingChannel();
		const transport = {};
		const seen: unknown[] = [];

		openChannel(Ctor as any, transport, (channel) => seen.push(channel));
		openChannel(Ctor as any, transport, (channel) => seen.push(channel));
		await tick();

		expect(built.length).toBe(1);
		expect(seen.length).toBe(2);
		expect(seen[0]).toBe(seen[1]);
	});

	it("still answers a caller that arrives after the channel opened", async () => {
		const { built, Ctor } = countingChannel();
		const transport = {};

		openChannel(Ctor as any, transport, () => {});
		await tick();
		let late: unknown = null;
		openChannel(Ctor as any, transport, (channel) => {
			late = channel;
		});
		await tick();

		expect(built.length).toBe(1);
		expect(late).not.toBeNull();
	});

	it("gives separate transports separate channels", async () => {
		const { built, Ctor } = countingChannel();

		openChannel(Ctor as any, {}, () => {});
		openChannel(Ctor as any, {}, () => {});
		await tick();

		expect(built.length).toBe(2);
	});
});
