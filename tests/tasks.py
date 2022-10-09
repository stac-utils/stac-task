from stactask import Task


class NothingTask(Task):
    name = "nothing-task"
    description = "this task does nothing"

    def process(self):
        return self.items_as_dicts


class DerivedItemTask(Task):
    name = "derived-item-task"
    description = "this task creates a derived item"

    def process(self, parameter=None):
        assert parameter == "value"
        return [self.create_item_from_item(self.items_as_dicts[0])]