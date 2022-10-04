#!/usr/bin/env python
import json
from pathlib import Path

import vcr

from stactask import Task


testpath = Path(__file__).parent
cassettepath = testpath / 'fixtures' / 'cassettes'


class NothingTask(Task):
    name = 'nothing-task'
    description = 'this task does nothing'

    def process(self):
        return self.items


class DerivedItemTask(Task):
    name = 'derived-item-task'
    description = 'this task creates a dervied item'

    def process(self):
        return [self.create_item_from_item(self.items[0])]


def get_test_items(name='sentinel2-items'):
    filename = testpath / "fixtures" / f"{name}.json"
    with open(filename) as f:
        items = json.loads(f.read())
    return items


def test_task_init():
    item_collection = get_test_items()
    t = NothingTask(item_collection)
    assert len(t._item_collection["features"]) == 1
    assert len(t.items) == 1
    assert t.logger.name == t.name
    assert t._tmpworkdir == True


def test_edit_items():
    items = get_test_items()
    t = NothingTask(items)
    t.process_definition['workflow'] = 'test-task-workflow'
    assert(t._item_collection['process']['workflow'] == 'test-task-workflow')


def test_edit_items():
    items = get_test_items()
    t = NothingTask(items)
    assert(t._item_collection['features'][0]['type'] == 'Feature')


def test_tmp_workdir():
    t = NothingTask(get_test_items())
    assert t._tmpworkdir == True
    workdir = t._workdir
    assert workdir.parts[-1].startswith("tmp")
    assert workdir.is_dir() == True
    del t
    assert workdir.is_dir() == False


def test_workdir():
    t = NothingTask(get_test_items(), workdir = testpath / 'test_task')
    assert(t._tmpworkdir == False)
    workdir = t._workdir
    assert(workdir.parts[-1] == 'test_task')
    assert(workdir.is_dir() == True)
    del t
    assert(workdir.is_dir() == True)    
    workdir.rmdir()
    assert(workdir.is_dir() == False)


def test_parameters():
    items = get_test_items()
    t = NothingTask(items)
    assert t.process_definition["workflow"] == "cog-archive"
    assert (
        t.upload_options["path_template"]
        == items["process"]["upload_options"]["path_template"]
    )


def test_process():
    items = get_test_items()
    t = NothingTask(items)
    items = t.process()
    assert(items[0]['type'] == 'Feature')


def test_derived_item():
    t = DerivedItemTask(get_test_items())
    items = t.process()
    links = [l for l in items[0]['links'] if l['rel'] == 'derived_from']
    assert(len(links) == 1)
    self_link = [l for l in items[0]['links'] if l['rel'] == 'self'][0]
    assert(links[0]['href'] == self_link['href'])


def test_task_handler():
    items = get_test_items()
    self_link = [l for l in items['features'][0]['links'] if l['rel'] == 'self'][0]
    output_items = DerivedItemTask.handler(items)
    derived_link = [
        l for l in output_items["features"][0]["links"] if l["rel"] == "derived_from"
    ][0]
    assert derived_link["href"] == self_link["href"]


#@vcr.use_cassette(str(cassettepath/'download_assets'))
#def test_download_assets():
#    t = NothingTask(get_test_items(), workdir=testpath/'test-task-download-assets')
#    t.download_assets(['metadata'])
#    filename = Path(t.items[0]['assets']['metadata']['href'])
#    assert(filename.is_file() == True)
#    t._tmpworkdir = True
#    del t
#    assert(filename.is_file() == False)


if __name__ == "__main__":
    output = NothingTask.cli()
