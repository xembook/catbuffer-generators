class GeneratorUtils:
    """Generator utility class"""

    @staticmethod
    def bufferToUint(buffer: bytes) -> int:
        return int.from_bytes(buffer, byteorder='little', signed=False)

    @staticmethod
    def uintToBuffer(uint: int, buffer_size: int) -> bytes:
        return uint.to_bytes(buffer_size, byteorder='little', signed=False)

    @staticmethod
    def concatTypedArrays(array1, array2):
        return array1 + array2

    @staticmethod
    def uint8ToInt8(number: int) -> int:
        if number > 127:
            return number - 256
        else:
            return number

    @staticmethod
    def getTransactionPaddingSize(size: int, alignment: int) -> int:
        if 0 == size % alignment:
            return 0
        else:
            return alignment - (size % alignment)

    @staticmethod
    def getBytes(binary: bytes, size: int) -> bytes:
        if size > len(binary):
            raise Exception('size should not exceed {0}. The value of size was: {1}'.format(len(binary), size))
        return binary[0:size]

    @staticmethod
    def listSplice(target, start, delete_count=None, *items):
        """Remove existing elements and/or add new elements to a list.

        target        the target list (will be changed)
        start         index of starting position
        delete_count  number of items to remove (default: len(target) - start)
        *items        items to insert at start index

        Returns a new list of removed items (or an empty list)
        """
        if delete_count is None:
            delete_count = len(target) - start

        # store removed range in a separate list and replace with *items
        total = start + delete_count
        removed = target[start:total]
        target[start:total] = items

        return removed
