# catbuffer

The catbuffer library helps serialize and deserialize NEM's Catapult entities in Python applications. 

The library's main client is a future NEM Python SDK (nem2-sdk-python) but it can be used alone.
 
It is generated using [catbuffer-generators](https://github.com/nemtech/catbuffer-generators) from the [catbuffer](https://github.com/nemtech/catbuffer) specification. 

The generated code is in Python version >= 3.7.

As catbuffer schema uses upper and lower Camel Case naming convention, the generated code also uses this convention for easier cross-referencing between the code and the schema.

Thus, you may disable PEP 8 naming convention violation inspection in your IDE.
