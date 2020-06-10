import java.io.DataInputStream;
import java.io.SequenceInputStream;
import java.io.ByteArrayInputStream;

/** Factory in charge of creating the right transaction builder from the streamed data. */
public class TransactionBuilderFactory {

    /**
    * It creates the rigth embbeded transaction builder from the stream data.
    *
    * @param stream the stream
    * @return the EmbeddedTransactionBuilder subclass
    */
    public static EmbeddedTransactionBuilder createEmbeddedTransactionBuilder(final DataInputStream stream) {

        EmbeddedTransactionBuilder headerBuilder = EmbeddedTransactionBuilder.loadFromBinary(stream);
% for name in generator.schema:
    <%
        layout = generator.schema[name].get("layout", [{type:""}])
        entityTypeValue = next(iter([x for x in layout if x.get('type','') == 'EntityType']),{}).get('value',0)
    %>\
    %if (entityTypeValue > 0 and 'Aggregate' not in name and 'Block' not in name):
        if (headerBuilder.getType().getValue() == ${entityTypeValue}) {
            ${name}BodyBuilder bodyBuilder = ${name}BodyBuilder.loadFromBinary(stream);
            SequenceInputStream concatenate = new SequenceInputStream(
            new ByteArrayInputStream(headerBuilder.serialize()),
            new ByteArrayInputStream(bodyBuilder.serialize()));
            return Embedded${name}Builder.loadFromBinary(new DataInputStream(concatenate));
        }
    %endif
% endfor
        return headerBuilder;
    }

    /**
    * It creates the right transaction builder from the stream data.
    *
    * @param stream the stream
    * @return the TransactionBuilder subclass
    */
    public static TransactionBuilder createTransactionBuilder(final DataInputStream stream) {

        TransactionBuilder headerBuilder = TransactionBuilder.loadFromBinary(stream);
% for name in generator.schema:
    <%
        layout = generator.schema[name].get("layout", [{type:""}])
        entityTypeValue = next(iter([x for x in layout if x.get('type','') == 'EntityType']),{}).get('value',0)
    %>\
    %if (entityTypeValue > 0  and 'Aggregate' not in name and 'Block' not in name):
        if (headerBuilder.getType().getValue() == ${entityTypeValue}) {
            ${name}BodyBuilder bodyBuilder = ${name}BodyBuilder.loadFromBinary(stream);
            SequenceInputStream concatenate = new SequenceInputStream(
            new ByteArrayInputStream(headerBuilder.serialize()),
            new ByteArrayInputStream(bodyBuilder.serialize()));
            return ${name}Builder.loadFromBinary(new DataInputStream(concatenate));
        }
    %elif (entityTypeValue > 0 and 'Block' not in name):
        if (headerBuilder.getType().getValue() == ${entityTypeValue}) {
            AggregateTransactionBodyBuilder bodyBuilder = AggregateTransactionBodyBuilder.loadFromBinary(stream);
            SequenceInputStream concatenate = new SequenceInputStream(
            new ByteArrayInputStream(headerBuilder.serialize()),
            new ByteArrayInputStream(bodyBuilder.serialize()));
            return ${name}Builder.loadFromBinary(new DataInputStream(concatenate));
        }
    %endif
% endfor
        return headerBuilder;
    }

}
