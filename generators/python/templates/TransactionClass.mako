## NOTE: do *not* touch `buffered` in render definitions, it will completely break output
<%
    python_lib_import_statements = []
    catbuffer_lib_import_statements = []
    for a in sorted(generator.required_import):
        if str(a).startswith('from .'):
            catbuffer_lib_import_statements.append(a)
        else:
            python_lib_import_statements.append(a)
%>\
from __future__ import annotations

# pylint: disable=unused-import

% for a in python_lib_import_statements:
${a}
% endfor
from .GeneratorUtils import GeneratorUtils
% for a in catbuffer_lib_import_statements:
${a}
% endfor

# from binascii import hexlify

class ${generator.generated_class_name}${'(' + str(generator.generated_base_class_name) + ')' if generator.generated_base_class_name is not None else ''}:
    """${helper.capitalize_first_character(generator.comments)}.

    Attributes:
% for a in [a for a in generator.attributes if not a.attribute_is_super and not a.attribute_is_inline and not a.kind == helper.AttributeKind.SIZE_FIELD and not a.attribute_is_reserved and a.attribute_name != 'size']:
    % if a.attribute_name.endswith('TransactionBody'):
        body: ${helper.capitalize_first_character(a.attribute_comment)}.
    % else:
        ${a.attribute_name}: ${helper.capitalize_first_character(a.attribute_comment)}.
    % endif
% endfor
    """
% if generator.name.endswith('TransactionBody'):
% for a in [a for a in generator.attributes if not a.attribute_is_super and not a.attribute_is_inline and not a.kind == helper.AttributeKind.SIZE_FIELD and not a.attribute_is_reserved and a.attribute_name != 'size']:
  % if a.kind == helper.AttributeKind.ARRAY:
    ${a.attribute_name} = []
  % elif a.kind == helper.AttributeKind.VAR_ARRAY:
    ${a.attribute_name} = []
  % elif a.kind == helper.AttributeKind.FILL_ARRAY:
    ${a.attribute_name} = []
  % elif a.kind == helper.AttributeKind.BUFFER:
    ${a.attribute_name} = bytes()
  % elif a.kind == helper.AttributeKind.CUSTOM and a.attribute_base_type == 'byte' and a.attribute_size > 8:
    ${a.attribute_name} = bytes(${a.attribute_size})
  % elif a.kind == helper.AttributeKind.CUSTOM and a.attribute_base_type == 'enum':
    ${a.attribute_name} = ${a.attribute_var_type}(0).value
  % elif a.kind == helper.AttributeKind.CUSTOM and a.attribute_base_type == 'struct':
    ${a.attribute_name} = None # ${a.attribute_var_type}
  % elif a.kind == helper.AttributeKind.FLAGS:
    ${a.attribute_name} = []
  %elif a.attribute_var_type != 'int':
    ${a.attribute_name} = ${a.attribute_var_type}().${helper.decapitalize_first_character(a.attribute['type'])}
  % else:
    ${a.attribute_name} = ${a.attribute_var_type}()
  % endif
% endfor

% elif generator.name.endswith('Transaction'):
##  CONSTRUCTOR:
  % if generator.name == 'Transaction':
    def __init__(self, signerPublicKey, version, network, type):
        """Constructor.
        Args:
            signerPublicKey: Entity signer's public key.
            version: Entity version.
            network: Entity network.
            type: Entity type.
        """
        self.signature = bytes(${next(a for a in generator.attributes if a.attribute_name == 'signature').attribute_size})
        self.signerPublicKey = signerPublicKey
        self.version = version
        self.network = network
        self.type = type

        self.fee = 0
        self.deadline = 0
  % elif generator.name == 'EmbeddedTransaction':
    def __init__(self, signerPublicKey: KeyDto, version, network: NetworkTypeDto, type):
        """Constructor.
        Args:
            signerPublicKey: Entity signer's public key.
            version: Entity version.
            network: Entity network.
            type: Entity type.

        """
        self.signerPublicKey = signerPublicKey
        self.version = version
        self.network = network
        self.type = type

  % else:
    % for a in generator.immutable_attributes:
    % if a.attribute_base_type == 'enum':
    ${helper.snake_case(a.attribute_name).upper()} = 0x${'{:x}'.format(a.attribute_value)}
    % else:
    ${helper.snake_case(a.attribute_name).upper()} = ${a.attribute_value}
    % endif
    % endfor

    def __init__(self, signerPublicKey: KeyDto, network: NetworkTypeDto):
        """Constructor.
        Args:
            signerPublicKey: Entity signer's public key.
            network: Entity network.
        """
        super().__init__(signerPublicKey, self.VERSION, network, self.ENTITY_TYPE)

        self.body = ${ next(a for a in generator.attributes if a.attribute_name.endswith('TransactionBody')).attribute_class_name }()
  % endif

% endif # TransactionBody
% if 'AggregateTransactionBody' in generator.generated_class_name:
    @staticmethod
    def _loadEmbeddedTransactions(transactions, payload: bytes, payloadSize: int):
        remainingByteSizes = payloadSize
        while remainingByteSizes > 0:
            item = EmbeddedTransactionBuilderFactory.createBuilder(payload)
            transactions.append(item)
            itemSize = item.getSize() + GeneratorUtils.getTransactionPaddingSize(item.getSize(), 8)
            remainingByteSizes -= itemSize
            payload = payload[itemSize:]
        return payload

% endif
##  LOAD FROM BINARY:
<%def name="renderReader(a)" filter="trim" buffered="True">
    % if a.kind == helper.AttributeKind.SIMPLE:
        ${a.attribute_name} = GeneratorUtils.bufferToUint(GeneratorUtils.getBytes(bytes_, ${a.attribute_size}))  # kind:SIMPLE
        bytes_ = bytes_[${a.attribute_size}:]
    % elif a.kind == helper.AttributeKind.BUFFER:
        ${a.attribute_name} = GeneratorUtils.getBytes(bytes_, ${a.attribute_size})  # kind:BUFFER
        bytes_ = bytes_[${a.attribute_size}:]
    % elif a.kind == helper.AttributeKind.SIZE_FIELD:
        ${a.attribute_name} = GeneratorUtils.bufferToUint(GeneratorUtils.getBytes(bytes_, ${a.attribute_size}))  # kind:SIZE_FIELD
        bytes_ = bytes_[${a.attribute_size}:]
    % elif a.kind == helper.AttributeKind.ARRAY:
        ${a.attribute_name} = []  # kind:ARRAY
        for _ in range(${a.attribute_size}):
            item = ${a.attribute_class_name}.loadFromBinary(bytes_)
        % if a.attribute_base_type == 'struct':
            ${a.attribute_name}.append(item.as_tuple())
        % elif a.attribute_base_type == 'enum':
            ${a.attribute_name}.append(item)
        % else:
            ${a.attribute_name}.append(item.${helper.decapitalize_first_character(a.attribute['type'])})
        % endif
            bytes_ = bytes_[item.getSize():]
    % elif a.kind == helper.AttributeKind.CUSTOM and a.conditional_read_before:
        ${a.attribute_name} = ${a.attribute_class_name}.loadFromBinary(${a.attribute['condition']}Condition).${helper.decapitalize_first_character(a.attribute['type'])}  # kind:CUSTOM3
    % elif a.kind == helper.AttributeKind.CUSTOM and a.attribute_base_type == 'enum':
        ${a.attribute_name}_ = ${a.attribute_class_name}.loadFromBinary(bytes_)  # kind:CUSTOM2
        ${a.attribute_name} = ${a.attribute_name}_.value
        bytes_ = bytes_[${a.attribute_name}_.getSize():]
    % elif a.kind == helper.AttributeKind.CUSTOM and a.attribute_base_type == 'byte':
        ${a.attribute_name}_ = ${a.attribute_class_name}.loadFromBinary(bytes_)  # kind:CUSTOM1_byte
        ${a.attribute_name} = ${a.attribute_name}_.${helper.decapitalize_first_character(a.attribute['type'])}
        bytes_ = bytes_[${a.attribute_name}_.getSize():]
    % elif a.kind == helper.AttributeKind.CUSTOM:
      % if a.attribute_is_aggregate:
        body = ${a.attribute_class_name}.loadFromBinary(bytes_)  # kind:CUSTOM1_nonbyte
        bytes_ = bytes_[body.getSize():]
      % else:
        ${a.attribute_name} = ${a.attribute_class_name}.loadFromBinary(bytes_)  # kind:CUSTOM1_nonbyte
        bytes_ = bytes_[${a.attribute_name}.getSize():]
        ${a.attribute_name} = ${a.attribute_name}.as_tuple()
      % endif
    % elif a.kind == helper.AttributeKind.FILL_ARRAY:
        ${a.attribute_name}_ = []
        bytes_ = GeneratorUtils.loadFromBinary(${a.attribute_class_name}, ${a.attribute_name}_, bytes_, len(bytes_))
        ${a.attribute_name} = list(map(lambda e: e.as_tuple(), ${a.attribute_name}_))
    % elif a.kind == helper.AttributeKind.FLAGS:
        ${a.attribute_name} = ${a.attribute_class_name}.bytesToFlags(bytes_, ${a.attribute_size})  # kind:FLAGS
        bytes_ = bytes_[${a.attribute_size}:]
    % elif a.kind == helper.AttributeKind.VAR_ARRAY:
        transactions = []
        bytes_ = ${generator.generated_class_name}._loadEmbeddedTransactions(transactions, bytes_, ${a.attribute_size})
    % else:
        FIX ME!
    % endif
</%def>\
<%def name="renderCondition(a, useSelf=True)" filter="trim">
    ${helper.get_condition_operation_text(a.attribute['condition_operation']).format(('self.' if useSelf else '') + a.attribute['condition'], helper.get_generated_class_name(a.condition_type_attribute['type'], a.condition_type_attribute, generator.schema) + '.' + helper.create_enum_name(a.attribute['condition_value']) + '.value')}
</%def>\
    @classmethod
    def loadFromBinary(cls, payload: bytes) -> ${generator.generated_class_name}:
        """Creates an instance of ${generator.generated_class_name} from binary payload.
        Args:
            payload: Byte payload to use to serialize the object.
        Returns:
            Instance of ${generator.generated_class_name}.
        """
        bytes_ = bytes(payload)
    % if generator.base_class_name is not None:
        superObject = ${generator.generated_base_class_name}.loadFromBinary(bytes_)
        assert cls.VERSION == superObject.version, 'Invalid entity version ({})'.format(superObject.version)
        assert cls.ENTITY_TYPE == superObject.type, 'Invalid entity type ({})'.format(superObject.type)
        bytes_ = bytes_[superObject.getSize():]
    % endif
    % for a in set([(a.attribute['condition'], a.attribute_size, a.conditional_read_before) for a in generator.attributes if not a.attribute_is_super and not a.attribute_is_inline and a.conditional_read_before and a.attribute_is_conditional]):
        ${a[0]}Condition = bytes_[0:${a[1]}]
        bytes_ = bytes_[${a[1]}:]
    % endfor

    % for a in [a for a in generator.attributes if not a.attribute_is_super and not a.attribute_is_inline and not a.conditional_read_before]:
        %if a.attribute_is_conditional:
        ${a.attribute_name} = None
        if ${renderCondition(a, useSelf=False) | trim}:
            ## handle py indents
            % for line in map(lambda a: a.strip(), renderReader(a).splitlines()):
            ${line}
            % endfor
        % else:
        ${renderReader(a) | trim}
        %endif
    % endfor
    % for a in [a for a in generator.attributes if not a.attribute_is_super and not a.attribute_is_inline and a.conditional_read_before]:
        ${a.attribute_name} = None
        if ${renderCondition(a, useSelf=False) | trim}:
            ## handle py indents
            % for line in map(lambda a: a.strip(), renderReader(a).splitlines()):
            ${line}
            % endfor
    % endfor

% if generator.name == 'EmbeddedTransaction':
        # create object and call
        result = EmbeddedTransactionBuilder(signerPublicKey, version, network, type)
        return result
% elif generator.name == 'Transaction':
        # create object and call
        result = TransactionBuilder(signerPublicKey, version, network, type)
        result.signature = signature
        result.fee = fee
        result.deadline = deadline
        return result
% else:
        # create object and call
    % if generator.name.endswith('TransactionBody'):
        result = ${generator.generated_class_name}()
    % else:
        result = ${generator.generated_class_name}(superObject.signerPublicKey, superObject.network)
        % if generator.base_class_name.endswith('EmbeddedTransaction'):
        # nothing needed to copy into EmbeddedTransaction
        % else:
        result.signature = superObject.signature
        result.fee = superObject.fee
        result.deadline = superObject.deadline
        % endif:
    % endif
    % for a in [a for a in generator.attributes if not a.attribute_is_super and not a.attribute_is_inline and not a.kind == helper.AttributeKind.SIZE_FIELD and not a.attribute_is_reserved and a.attribute_name != 'size']:
      % if a.attribute_name.endswith('TransactionBody'):
        result.body = body
      % else:
        result.${a.attribute_name} = ${a.attribute_name}
      % endif
    % endfor
        return result
% endif

% for a in [a for a in generator.attributes if a.attribute_is_inline and not a.kind == helper.AttributeKind.SIZE_FIELD and not a.attribute_is_reserved and a.attribute_name != 'size']:
    @property
    def ${a.attribute_name}(self):
        return self.body.${a.attribute_name}

% endfor
% if 'AggregateTransactionBody' in generator.generated_class_name:
    @classmethod
    def _serialize_aligned(cls, transaction: EmbeddedTransactionBuilder) -> bytes:
        """Serializes an embeded transaction with correct padding.
        Returns:
            Serialized embedded transaction.
        """
        bytes_ = transaction.serialize()
        padding = bytes(GeneratorUtils.getTransactionPaddingSize(len(bytes_), 8))
        return GeneratorUtils.concatTypedArrays(bytes_, padding)

    @classmethod
    def _getSize_aligned(cls, transaction: EmbeddedTransactionBuilder) -> int:
        """Serializes an embeded transaction with correct padding.
        Returns:
            Serialized embedded transaction.
        """
        size = transaction.getSize()
        paddingSize = GeneratorUtils.getTransactionPaddingSize(size, 8)
        return size + paddingSize
% endif
## SIZE:
<%def name="renderSize(a)" filter="trim"  buffered="True">\
    % if a.kind == helper.AttributeKind.SIMPLE:
        size += ${a.attribute_size}  # ${a.attribute_name}
    % elif a.kind == helper.AttributeKind.SIZE_FIELD:
        size += ${a.attribute_size}  # ${a.attribute_name}
    % elif a.kind == helper.AttributeKind.BUFFER:
        size += len(self.${a.attribute_name})
    % elif a.kind == helper.AttributeKind.VAR_ARRAY:
        for _ in self.${a.attribute_name}:
            size += self._getSize_aligned(_)
    % elif a.kind == helper.AttributeKind.ARRAY or a.kind == helper.AttributeKind.FILL_ARRAY:
        for _ in self.${a.attribute_name}:
        % if a.attribute_base_type == 'struct':
            size += ${a.attribute_class_name}.from_tuple(_).getSize()
        % else:
            size += ${a.attribute_class_name}(_).getSize()
        % endif
    % elif a.kind == helper.AttributeKind.FLAGS:
        size += ${a.attribute_size}  # ${a.attribute_name}
    % else:
      % if a.attribute_name.endswith('TransactionBody'):
        size += self.body.getSize()
      % else:
        % if a.attribute_base_type == 'struct':
        size += ${a.attribute_class_name}.from_tuple(self.${a.attribute_name}).getSize()
        % else:
        size += ${a.attribute_class_name}(self.${a.attribute_name}).getSize()
        % endif
      % endif
    % endif
</%def>\
    def getSize(self) -> int:
        """Gets the size of the object.
        Returns:
            Size in bytes.
        """
        size = ${'super().getSize()' if generator.base_class_name is not None else '0'}
% for a in [a for a in generator.attributes if not a.attribute_is_super and not a.attribute_is_inline]:
    % if a.attribute_is_conditional:
        if ${renderCondition(a) | trim}:
            ## handle py indents
            % for line in map(lambda a: a.strip(), renderSize(a).splitlines()):
            ${line}
            % endfor
    % else:
        ${renderSize(a).strip()}
    % endif
% endfor
        return size

##  SERIALIZE:
<%def name="renderSerialize(a)" filter="trim" buffered="True">\
    % if a.kind == helper.AttributeKind.SIMPLE and a.attribute_is_reserved:
        bytes_ = GeneratorUtils.concatTypedArrays(bytes_, GeneratorUtils.uintToBuffer(0, ${a.attribute_size}))
        # print("1. {:20s} : {}".format('${a.attribute_name}', hexlify(GeneratorUtils.uintToBuffer(0, ${a.attribute_size}))))
    % elif a.kind == helper.AttributeKind.SIMPLE and a.attribute_name != 'size':
        % if a.attribute_is_reserved:
        bytes_ = GeneratorUtils.concatTypedArrays(bytes_, GeneratorUtils.uintToBuffer(0, ${a.attribute_size}))  # kind:SIMPLE
        # print("2. {:20s} : {}".format('${a.attribute_name}', hexlify(GeneratorUtils.uintToBuffer(0, ${a.attribute_size}))))
        % else:
        bytes_ = GeneratorUtils.concatTypedArrays(bytes_, GeneratorUtils.uintToBuffer(self.${a.attribute_name}, ${a.attribute_size}))  # serial_kind:SIMPLE
        # print("2. {:20s} : {}".format('${a.attribute_name}', hexlify(GeneratorUtils.uintToBuffer(self.${a.attribute_name}, ${a.attribute_size}))))
        % endif
    % elif a.kind == helper.AttributeKind.SIMPLE and a.attribute_name == 'size':
        bytes_ = GeneratorUtils.concatTypedArrays(bytes_, GeneratorUtils.uintToBuffer(self.getSize(), ${a.attribute_size}))  # serial_kind:SIMPLE
        # print("3. {:20s} : {}".format('${a.attribute_name}', hexlify(GeneratorUtils.uintToBuffer(self.getSize(), ${a.attribute_size}))))
    % elif a.kind == helper.AttributeKind.BUFFER:
        bytes_ = GeneratorUtils.concatTypedArrays(bytes_, self.${a.attribute_name})  # kind:BUFFER
        # 4. ${a.attribute_name}
        # print("4. {:20s} : {}".format('${a.attribute_name}', hexlify(self.${a.attribute_name})))
    % elif a.kind == helper.AttributeKind.SIZE_FIELD:
        ## note: it would be best to access parent 'kind'
      % if 'AggregateTransactionBody' in generator.generated_class_name and a.attribute_name == 'payloadSize':
        # calculate payload size
        size_value = 0
        for _ in self.${a.parent_attribute['name']}:
            size_value += self._getSize_aligned(_)
      % else:
        size_value = len(self.${a.parent_attribute['name']})
      % endif
        bytes_ = GeneratorUtils.concatTypedArrays(bytes_, GeneratorUtils.uintToBuffer(size_value, ${a.attribute_size}))  # kind:SIZE_FIELD
        # print("5. {:20s} : {}".format('${a.attribute_name}', hexlify(GeneratorUtils.uintToBuffer(size_value, ${a.attribute_size}))))
    % elif a.kind == helper.AttributeKind.ARRAY or a.kind == helper.AttributeKind.FILL_ARRAY:
        for _ in self.${a.attribute_name}: # kind:ARRAY|FILL_ARRAY
        % if a.attribute_base_type == 'struct':
            bytes_ = GeneratorUtils.concatTypedArrays(bytes_, ${a.attribute_class_name}.from_tuple(_).serialize())
            # print("6. {:20s} : {}".format('${a.attribute_name}', hexlify(${a.attribute_class_name}.from_tuple(_).serialize())))
        % else:
            bytes_ = GeneratorUtils.concatTypedArrays(bytes_, ${a.attribute_class_name}(_).serialize())
            # print("6. {:20s} : {}".format('${a.attribute_name}', hexlify(${a.attribute_class_name}(_).serialize())))
        % endif
    % elif a.kind == helper.AttributeKind.VAR_ARRAY:
        for _ in self.${a.attribute_name}: # kind:VAR_ARRAY
            bytes_ = GeneratorUtils.concatTypedArrays(bytes_, self._serialize_aligned(_))
            # print("7. {:20s} : {}".format('${a.attribute_name}', hexlify(self._serialize_aligned(_))))
    % elif a.kind == helper.AttributeKind.CUSTOM:
      % if a.attribute_name.endswith('TransactionBody'):
        bytes_ = GeneratorUtils.concatTypedArrays(bytes_, self.body.serialize())  # kind:CUSTOM
        # print("8. {:20s} : ".format('${a.attribute_name}'))
      % else:
        % if a.attribute_base_type == 'struct':
        bytes_ = GeneratorUtils.concatTypedArrays(bytes_, ${a.attribute_class_name}.from_tuple(self.${a.attribute_name}).serialize())  # kind:CUSTOM
        # print("8. {:20s} : {}".format('${a.attribute_name}', hexlify(${a.attribute_class_name}.from_tuple(self.${a.attribute_name}).serialize())))
        % else:
        bytes_ = GeneratorUtils.concatTypedArrays(bytes_, ${a.attribute_class_name}(self.${a.attribute_name}).serialize())  # kind:CUSTOM
        # print("8. {:20s} : {}".format('${a.attribute_name}', hexlify(${a.attribute_class_name}(self.${a.attribute_name}).serialize())))
        % endif
      % endif
    % elif a.kind == helper.AttributeKind.FLAGS:
        bytes_ = GeneratorUtils.concatTypedArrays(bytes_, GeneratorUtils.uintToBuffer(${a.attribute_class_name}.flagsToInt(self.${a.attribute_name}), ${a.attribute_size}))  # kind:FLAGS
        # print("9. {:20s}".format('${a.attribute_name}'))
    % else:
        # Ignored serialization: ${a.attribute_name} ${a.kind}
    % endif
</%def>\
    def serialize(self) -> bytes:
        """Serializes self to bytes.
        Returns:
            Serialized bytes.
        """
        bytes_ = bytes()
 % if generator.base_class_name is not None:
        bytes_ = GeneratorUtils.concatTypedArrays(bytes_, super().serialize())
% endif
% for a in [a for a in generator.attributes if not a.attribute_is_super and not a.attribute_is_inline]:
    % if a.attribute_is_conditional:
        if ${renderCondition(a) | trim}:
            ## handle py indents
            % for line in map(lambda a: a.strip(), renderSerialize(a).splitlines()):
            ${line}
            % endfor
    % else:
        ${renderSerialize(a)}
    % endif
% endfor
        return bytes_