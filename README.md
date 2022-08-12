# STAC Task (stactask)

This Python library consists of the Task class, which is used to create custom tasks based
on a "STAC In, STAC Out" approach. The Task class acts as wrapper around custom code and provides
several convenience methods for modifying STAC Items, creating derived Items, and providing a CLI.

This library is currently under development and may not be a final standalone repo, insteading 
being merged into [stactools](https://github.com/stac-utils/stactools), 
see [#345](https://github.com/stac-utils/stactools/issues/345). It is based on a [branch of
cirrus-lib](https://github.com/cirrus-geo/cirrus-lib/tree/features/task-class) except
aims to be more generic.