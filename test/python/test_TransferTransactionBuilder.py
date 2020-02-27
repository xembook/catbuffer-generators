import base64
import unittest
import importlib

builderModulePath = '_generated.python.TransferTransactionBuilder'

try:
    builderModule = importlib.import_module(builderModulePath)
    builderClass = builderModule.TransferTransactionBuilder

    class TestTransferTransactionBuilder(unittest.TestCase):
        def setUp(self):
            # known binary payload string
            self.payload = 'D4000000000000006AE7B860A2F24F9E5618C25E9175761A051AAEE3910BCC8B3B42AFC0A50F586F7CDD0CE9272E' \
                           'CA801D3912628B8A761AAEF55FFB89E73F06E133B78ACA3EB30DC2F93346E27CE6AD1A9F8F5E3066F8326593A406' \
                           'BDF357ACB041E2F9AB402EFE0000000001905441000000000000000077224DFB010000009050B9837EFAB4BBE8A4' \
                           'B9BB32D812F9885C00D8FC1650E14203040000000000BA36BD286FB7F2670A00000000000000D787D9329996A177' \
                           '060000000000000029CF5FD941AD25D50500000000000000004E454D'
            # load from known binary payload
            self.builder = builderClass.loadFromBinary(bytes.fromhex(self.payload))
            # known deserialized payload transaction data for assertions
            self.type_ = 16724
            self.version = 1
            self.size = 212
            self.messageType = 0
            self.messageText = 'NEM'  # hex: '4E454D'
            self.signerPublicKey = 'C2F93346E27CE6AD1A9F8F5E3066F8326593A406BDF357ACB041E2F9AB402EFE'
            self.networkType = '144'  # MIJIN_TEST
            self.deadline = 8511103607
            self.recipientAddress = b'SBILTA367K2LX2FEXG5TFWAS7GEFYAGY7QLFBYKC'
            mosaicId1 = '67F2B76F28BD36BA'  # 7490250818323297978
            mosaicId2 = '77A1969932D987D7'  # 8620336746491119575
            mosaicId3 = 'D525AD41D95FCF29'  # 15358872602548358953
            self.mosaicIds = [mosaicId1, mosaicId2, mosaicId3]

        def test_type(self):
            type_ = self.builder.getType_()
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
            networkType = self.builder.getNetwork()
            self.assertEqual(str(networkType), self.networkType)

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
    print("DETAIL: Missing module path '{0}' in repository/submodule: catbuffer-generators/catbuffer.".format(builderModulePath))
    print("POSSIBLE CAUSES:")
    print("    1. The generated code is not in catbuffer-generators/catbuffer directory.")
    print("       Try: Run ./scripts/generate_python.sh.")
    print("    2. The catbuffer-generators/catbuffer directory is not in the search path for module files.")
    print("       Try: Depending on your IDE, either Mark Directory (catbuffer) as Sources Root or check PYTHONPATH environment variable.")
    raise
