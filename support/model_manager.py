# To Create a model modelname:
# POST http://packager/model/{modelname}
# while response.complete is not true, GET {response.link} to poll for completeness

# To Delete a model modelname:
# DELETE http://packager/model/{modelname}
# while response.complete is not true, GET {response.link} to poll for completeness

