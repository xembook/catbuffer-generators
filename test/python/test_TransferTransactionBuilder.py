import base64
import unittest
import importlib
import os
from pathlib import Path

path = Path(os.getcwd())
runningTestInGenerators = path.parts[len(path.parts) - 1] == 'python' and \
                          path.parts[len(path.parts) - 2] == 'test' and \
                          path.parts[len(path.parts) - 3] == 'catbuffer-generators'

if runningTestInGenerators:
    builderModulePath = '_generated.python.TransferTransactionBuilder'
    print("INFO: Test code generated in catbuffer:", builderModulePath)
else:
    builderModulePath = 'symbol_catbuffer.TransferTransactionBuilder'
    print("INFO: Test installed module:", builderModulePath)

try:
    builderModule = importlib.import_module(builderModulePath)
    builderClass = builderModule.TransferTransactionBuilder

    class TestTransferTransactionBuilder(unittest.TestCase):
        def setUp(self):
            # known binary payload string
            self.payload = 'D400000000000000F020BDED6F4895FF4BDFCF8CE615580A566F44CDDD0D6D87CE7EAB7D66A0206F63CBD1A707DC' \
                           'C2F4C98C3136819A0ECC163811C2ED78F2F3566C9C75463C7B019801508C58666C746F471538E43002B85B1CD542' \
                           'F9874B2861183919BA8787B60000000001905441000000000000000072D61F16060000009026D27E1D0A26CA4E31' \
                           '6F901E23E55C8711DB20DF11A7B20400030000000000BA36BD286FB7F2670A00000000000000D787D9329996A177' \
                           '060000000000000029CF5FD941AD25D50500000000000000004E454D'

            # load from known binary payload
            self.builder = builderClass.loadFromBinary(bytes.fromhex(self.payload))
            # known deserialized payload transaction data for assertions
            self.type_ = 16724
            self.version = 1
            self.size = 212
            self.messageType = 0
            self.messageText = 'NEM'  # hex: '4E454D'
            self.signerPublicKey = '9801508C58666C746F471538E43002B85B1CD542F9874B2861183919BA8787B6'
            self.networkType = 144  # MIJIN_TEST
            self.deadline = 26140989042
            self.recipientAddress = b'SATNE7Q5BITMUTRRN6IB4I7FLSDRDWZA34I2PMQ='
            mosaicId1 = '67F2B76F28BD36BA'  # 7490250818323297978
            mosaicId2 = '77A1969932D987D7'  # 8620336746491119575
            mosaicId3 = 'D525AD41D95FCF29'  # 15358872602548358953
            self.mosaicIds = [mosaicId1, mosaicId2, mosaicId3]

        def test_type(self):
            type_ = self.builder.getType().value
            self.assertEqual(type_, self.type_)

        def test_version(self):
            version = self.builder.getVersion()
            self.assertEqual(version, self.version)

        def test_size(self):
            size = self.builder.getSize()
            self.assertEqual(size, self.size)

        def test_signer_public_key(self):
            signerPublicKey = self.builder.getSignerPublicKey().key.hex().upper()
            self.assertEqual(str(signerPublicKey), self.signerPublicKey)

        def test_network_type(self):
            networkType = self.builder.getNetwork().value
            self.assertEqual(networkType, self.networkType)

        def test_deadline(self):
            deadline = self.builder.getDeadline().getTimestamp()
            self.assertEqual(deadline, self.deadline)

        def test_recipient_address(self):
            recipientAddress = base64.b32encode(
                bytes.fromhex(self.builder.getRecipientAddress().unresolvedAddress.hex()))
            self.assertEqual(recipientAddress, self.recipientAddress)

        def test_mosaic_ids(self):
            mosaics = self.builder.getMosaics()
            mosaicIds = []
            for mosaic in mosaics:
                mosaicId = mosaic.getMosaicId().unresolvedMosaicId.to_bytes(8, 'big').hex().upper()
                mosaicIds.append(mosaicId)
            self.assertListEqual(mosaicIds, self.mosaicIds)

        def test_serialize(self):
            serializedBytes = self.builder.serialize().hex().upper()
            self.assertEqual(serializedBytes, self.payload)

except ModuleNotFoundError as err:
    print("ERROR: ModuleNotFoundError:", err)
    if runningTestInGenerators:
        print("DETAIL: Missing module path '{0}' in submodule: catbuffer-generators/catbuffer.".format(builderModulePath))
        print("POSSIBLE CAUSES:")
        print("    1. The submodule is not in the search path for module files.")
        print("       Try: Mark Directory catbuffer as Sources Root or check PYTHONPATH environment variable.")
        print("    2. The generated code is not in catbuffer-generators/catbuffer directory.")
        print("       Try: Run ./scripts/generate_python.sh.")
    else:
        print("DETAIL: Missing module path '{0}'.".format(builderModulePath))
        print("POSSIBLE CAUSES:")
        print("    1. The '{0}' module is not in the search path for module files.".format(builderModulePath))
        print("       Try: Mark Directory catbuffer as Sources Root or check PYTHONPATH environment variable.")
    raise
