# enumeration of possible connection results
enum ConnectResult : uint8
	# client address could not be resolved
	resolve_error = 0

	# connection could not be established
	connect_error = 1

	# connection attempt was canceled
	connect_cancelled = 2

	# connection was successfully established
	connected = 3

