# pylint: disable=R0911,R0912

# Imports for creating embedded transaction builders
from .EmbeddedTransactionBuilder import EmbeddedTransactionBuilder
% for name in sorted(generator.schema):
<%
    layout = generator.schema[name].get("layout", [{type:""}])
    entityTypeValue = next(iter([x for x in layout if x.get('type','') == 'EntityType']),{}).get('value',0)
%>\
% if entityTypeValue > 0 and 'Aggregate' not in name and 'Block' not in name:
from .Embedded${name}Builder import Embedded${name}Builder
% endif
% endfor
# Imports for creating transaction builders
from .TransactionBuilder import TransactionBuilder
% for name in sorted(generator.schema):
<%
    layout = generator.schema[name].get("layout", [{type:""}])
    entityTypeValue = next(iter([x for x in layout if x.get('type','') == 'EntityType']),{}).get('value',0)
%>\
% if entityTypeValue > 0 and 'Block' not in name:
from .${name}Builder import ${name}Builder
% endif
% endfor


class TransactionBuilderFactory:
    """Factory in charge of creating the specific transaction builder from the binary payload.

    It has 2 class methods:
    (i) createEmbeddedTransactionBuilder
            Creates the specific embedded transaction builder from given payload.
    (ii) createTransactionBuilder
            Creates the specific transaction builder from given payload.
    """

    @classmethod
    def createEmbeddedTransactionBuilder(cls, payload) -> EmbeddedTransactionBuilder:
        """
        It creates the specific embedded transaction builder from the payload bytes.
        Args:
            payload: bytes
        Returns:
            the EmbeddedTransactionBuilder subclass
        """
        headerBuilder = EmbeddedTransactionBuilder.loadFromBinary(payload)
        entityType = headerBuilder.getType().value
% for name in generator.schema:
<%
    layout = generator.schema[name].get("layout", [{type:""}])
    entityTypeValue = next(iter([x for x in layout if x.get('type','') == 'EntityType']),{}).get('value',0)
%>\
% if entityTypeValue > 0 and 'Aggregate' not in name and 'Block' not in name:
        if entityType == ${entityTypeValue}:
            return Embedded${name}Builder.loadFromBinary(payload)
% endif
% endfor
        return headerBuilder

    @classmethod
    def createTransactionBuilder(cls, payload) -> TransactionBuilder:
        """
        It creates the specific transaction builder from the payload bytes.
        Args:
            payload: bytes
        Returns:
            the TransactionBuilder subclass
        """
        headerBuilder = TransactionBuilder.loadFromBinary(payload)
        entityType = headerBuilder.getType().value
% for name in generator.schema:
<%
    layout = generator.schema[name].get("layout", [{type:""}])
    entityTypeValue = next(iter([x for x in layout if x.get('type','') == 'EntityType']),{}).get('value',0)
%>\
    % if entityTypeValue > 0 and 'Block' not in name:
        if entityType == ${entityTypeValue}:
            return ${name}Builder.loadFromBinary(payload)
    % endif
% endfor
        return headerBuilder