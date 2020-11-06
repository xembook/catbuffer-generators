import * as YAML from 'yaml';
import * as assert from 'assert';
import * as fs from 'fs';
import * as builders from '../src';

const {createHash} = require('crypto');

interface BuilderTestItem {
    filename: string;
    builder: string;
    payload: string;
}

const hash = s => createHash('sha256').update(s).digest('hex');

const fromHexString = (hexString: string) =>
    new Uint8Array((hexString.match(/.{1,2}/g) || []).map(byte => parseInt(byte, 16)));

const toHexString = (bytes: Uint8Array) =>
    bytes.reduce((str, byte) => str + byte.toString(16).padStart(2, '0'), '').toUpperCase();

const vectorDirectory = 'test/vector';
const files = fs.readdirSync(vectorDirectory);

const items: BuilderTestItem[] = files.map(filename => {
    const yamlText = fs.readFileSync(vectorDirectory + '/' + filename, 'utf8');
    const yamlList = YAML.parse(yamlText)
    return yamlList.map((a: BuilderTestItem) => ({
        ...a, builder: a.builder.replace("AggregateTransactionBuilder",
            "AggregateCompleteTransactionBuilder"), filename
    } as BuilderTestItem));
}).reduce((acc, val) => acc.concat(val), []);


describe('serialize', function () {
    items.forEach(item => {
        it(item.filename + " - " + item.builder + " - " + hash(item.payload), function () {
            const builderClass = (<any>builders)[item.builder]
            const serializer = builderClass.loadFromBinary(fromHexString(item.payload));
            assert.equal(toHexString(serializer.serialize()), item.payload)
        });
    })
});
