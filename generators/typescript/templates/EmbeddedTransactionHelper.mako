import { EmbeddedTransactionBuilder } from './EmbeddedTransactionBuilder';
% for name in generator.schema:
<%
    layout = generator.schema[name].get("layout", [{type:""}])
    entityTypeValue = next(iter([x for x in layout if x.get('type','') == 'EntityType']),{}).get('value',0)
%>\
%if (entityTypeValue > 0 and 'Aggregate' not in name and 'Block' not in name):
import { Embedded${name}Builder } from './Embedded${name}Builder';
%endif
% endfor

/** Helper class for embedded transaction serialization */
export class EmbeddedTransactionHelper {

     /** Deserialize an embedded transaction builder from binary */
    public static loadFromBinary(payload: Uint8Array): EmbeddedTransactionBuilder {

        const header = EmbeddedTransactionBuilder.loadFromBinary(payload);
% for name in generator.schema:
    <%
        layout = generator.schema[name].get("layout", [{type:""}])
        entityTypeValue = next(iter([x for x in layout if x.get('type','') == 'EntityType']),{}).get('value',0)
    %>\
    %if (entityTypeValue > 0 and 'Aggregate' not in name and 'Block' not in name):

        if (header.type === ${entityTypeValue}) {
            return Embedded${name}Builder.loadFromBinary(payload);
        }
    %endif
% endfor

        return header;
    }

}
