import rio_stac.stac
import stac_task
from pystac import Item
from stac_task import HrefTask


class RioStacTask(HrefTask):
    def process_href(self, href: str) -> Item:
        return rio_stac.stac.create_stac_item(href)


stac_task.register_task("rio-stac", RioStacTask)
