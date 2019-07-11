# possible network identifiers.
# \note The lower 3 bits must be cleared because they are used for different purposes, e.g. resolvers
enum NetworkIdentifier : uint8
	# a default (zero) identifier that does not identify any known network
	zero = 0

	# mijin network identifier
	mijin = 0x60

	# mijin test network identifier
	mijin_test = 0x90

	# public network identifier
	public = 0x68

	# public test network identifier
	public_test = 0x98

