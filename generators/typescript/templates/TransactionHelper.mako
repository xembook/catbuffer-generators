import { TransactionBuilder } from "./TransactionBuilder";
% for name in generator.schema:
<%
    layout = generator.schema[name].get("layout", [{type:""}])
    entityTypeValue = next(iter([x for x in layout if x.get('type','') == 'EntityType']),{}).get('value',0)
%>\
%if (entityTypeValue > 0 and 'Block' not in name):
import { ${name}Builder } from './${name}Builder';
%endif
% endfor

/** Helper class for embedded transaction serialization */
export class TransactionHelper {

     /** Deserialize an transaction builder from binary */
    public static loadFromBinary(payload: Uint8Array): TransactionBuilder {

        const header = TransactionBuilder.loadFromBinary(payload);
% for name in generator.schema:
    <%
        layout = generator.schema[name].get("layout", [{type:""}])
        entityTypeValue = next(iter([x for x in layout if x.get('type','') == 'EntityType']),{}).get('value',0)
    %>\
    %if (entityTypeValue > 0 and 'Block' not in name):
        if (header.type === ${entityTypeValue}) {
            return  ${name}Builder.loadFromBinary(payload);
        }
    %endif
% endfor

        return header;
    }

}
