* support UUIDField - needs own APIEncoder, see eve/#102
* support DynamicField (there is one test for this, but definetely not enough)
* pagination tests
* support resource IDs other than '_id'
* save() and update() hooks on mongoengine classes: auto-generate etag and
  value of 'updated' field when performing actions on mongoengine side.
* Documentation: advanced usage, extending and hacking
