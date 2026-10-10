/** Typed transport boundary shared by the public QGIS facades. */

type OperationName<Operations> = Extract<keyof Operations, string>;

type OperationArgs<
	Operations,
	Name extends OperationName<Operations>,
> = Operations[Name] extends (...args: infer Args) => unknown ? Args : never;

type OperationResult<
	Operations,
	Name extends OperationName<Operations>,
> = Operations[Name] extends (...args: never[]) => infer Result
	? Awaited<Result>
	: never;

type MaybePromise<Value> = Value | PromiseLike<Value>;

type MissingTransportFallbacks<Operations> = {
	[Name in OperationName<Operations>]: (
		...args: OperationArgs<Operations, Name>
	) => MaybePromise<OperationResult<Operations, Name>>;
};

export type CallbackResponseMode = "identity" | "json" | "boolean";

interface TransportCallOptions {
	callbackResponse?: CallbackResponseMode;
}

type TransportMethod = (...args: unknown[]) => unknown;

interface ResolvedMethod {
	receiver: object;
	method: TransportMethod;
}

function resolveMethod(
	transport: unknown,
	methodName: string,
): ResolvedMethod | null {
	if (
		transport === null ||
		(typeof transport !== "object" && typeof transport !== "function")
	) {
		return null;
	}

	const receiver = transport as object;
	const candidate = (receiver as Record<string, unknown>)[methodName];
	if (typeof candidate !== "function") return null;
	return { receiver, method: candidate as TransportMethod };
}

function decodeCallback<Result>(
	response: unknown,
	mode: CallbackResponseMode,
): Result {
	if (mode === "boolean") return Boolean(response) as Result;
	if (mode === "json" && typeof response === "string") {
		try {
			return JSON.parse(response) as Result;
		} catch {
			// QWebChannel hosts may also return ordinary strings. JSON decoding is
			// deliberately best effort, matching the original facade behavior.
		}
	}
	return response as Result;
}

function invokeCallback<Result>(
	resolved: ResolvedMethod,
	args: readonly unknown[],
	mode: CallbackResponseMode,
): Promise<Result> {
	return new Promise((resolve, reject) => {
		try {
			resolved.method.apply(resolved.receiver, [
				...args,
				(response: unknown) => resolve(decodeCallback<Result>(response, mode)),
			]);
		} catch (error) {
			reject(error);
		}
	});
}

/**
 * Normalizes a QWebChannel callback method and a bridge Promise method behind
 * one operation-typed call. Each facade supplies its own finite operation map
 * and missing-transport fallbacks, so unknown method names cannot cross this
 * boundary and facade-specific policy remains visible at the facade.
 */
export class QgisTransportAdapter<Operations> {
	constructor(
		private readonly bridge: unknown,
		private readonly callbackTransport: unknown,
		private readonly missingTransport: MissingTransportFallbacks<Operations>,
	) {}

	async call<Name extends OperationName<Operations>>(
		methodName: Name,
		args: OperationArgs<Operations, Name>,
		options: TransportCallOptions = {},
	): Promise<OperationResult<Operations, Name>> {
		const callbackMethod = resolveMethod(this.callbackTransport, methodName);
		if (callbackMethod) {
			return invokeCallback<OperationResult<Operations, Name>>(
				callbackMethod,
				args,
				options.callbackResponse ?? "identity",
			);
		}

		const promiseMethod = resolveMethod(this.bridge, methodName);
		if (promiseMethod) {
			return (await promiseMethod.method.apply(
				promiseMethod.receiver,
				args,
			)) as OperationResult<Operations, Name>;
		}

		const fallback = this.missingTransport[methodName];
		return await fallback(...args);
	}
}
