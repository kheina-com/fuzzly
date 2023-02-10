# API
This is where much of the logic is defined for the fuzzly package. This is due to many of the internal models requiring access to the api and requiring client auth.

Defining endpoints in a separate directory allows for a neater package layout as well as removing the circular dependency with the client.
