/**
 * The page's single QWebChannel, shared by every caller on the same transport.
 *
 * Constructing a QWebChannel takes over `transport.onmessage`, so each transport can carry only
 * one channel. The first caller builds it; later callers, including the page's own scripts,
 * get the same channel object.
 */

type ChannelConstructor = new (
	transport: unknown,
	onInit: (channel: any) => void,
) => unknown;

interface Entry {
	channel?: any;
	waiting: Array<(channel: any) => void>;
}

const entries = new WeakMap<object, Entry>();

/** Calls `onReady` with the channel for `transport`, building it on first use. */
export function openChannel(
	Ctor: ChannelConstructor,
	transport: object,
	onReady: (channel: any) => void,
): void {
	let entry = entries.get(transport);
	if (!entry) {
		const created: Entry = { waiting: [] };
		entries.set(transport, created);
		entry = created;
		new Ctor(transport, (channel) => {
			created.channel = channel;
			for (const waiter of created.waiting.splice(0)) waiter(channel);
		});
	}
	if (entry.channel !== undefined) {
		const channel = entry.channel;
		queueMicrotask(() => onReady(channel));
	} else {
		entry.waiting.push(onReady);
	}
}
