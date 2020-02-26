# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2017 by the GFDRR / World Bank
#
# This file is part of ThinkHazard.
#
# ThinkHazard is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# ThinkHazard is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# ThinkHazard.  If not, see <http://www.gnu.org/licenses/>.

import logging
import rasterio
from sqlalchemy import func

from thinkhazard.models import HazardSet, Layer
from thinkhazard.processing import BaseProcessor


logger = logging.getLogger(__name__)


class Completer(BaseProcessor):
    @staticmethod
    def argument_parser():
        parser = BaseProcessor.argument_parser()
        parser.add_argument(
            "--hazardset_id",
            dest="hazardset_id",
            action="store",
            help="The hazardset id",
        )
        return parser

    def do_execute(self, hazardset_id=None):
        if self.force:
            try:
                logger.info("Resetting all hazardsets to incomplete state")
                with self.dbsession.begin_nested():
                    hazardsets = self.dbsession.query(HazardSet)
                    if hazardset_id is not None:
                        hazardsets = hazardsets.filter(HazardSet.id == hazardset_id)
                    hazardsets.update(
                        {HazardSet.complete: False, HazardSet.processed: None}
                    )
            except:
                logger.error("Batch reset to incomplete state failed", exc_info=True)

        ids = self.dbsession.query(HazardSet.id)
        if not self.force:
            ids = ids.filter(HazardSet.complete.is_(False))
        if hazardset_id is not None:
            ids = ids.filter(HazardSet.id == hazardset_id)
        ids = ids.order_by(HazardSet.id)
        for id in ids:
            try:
                # complete can be either True or an error message
                complete = self.complete_hazardset(id[0])
                with self.dbsession.begin_nested():
                    if complete is not True:
                        hazardset = self.dbsession.query(HazardSet).get(id)
                        hazardset.complete_error = complete
                        logger.warning(
                            "Hazardset {} incomplete: {}".format(hazardset.id, complete)
                        )
            except Exception:
                logger.error(
                    "An error occurred with hazardset {}".format(id), exc_info=True
                )

    def complete_hazardset(self, hazardset_id, dry_run=False):
        logger.info("Completing hazardset {}".format(hazardset_id))
        hazardset = self.dbsession.query(HazardSet).get(hazardset_id)
        if hazardset is None:
            raise Exception("Hazardset {} does not exist.".format(hazardset_id))

        hazardtype = hazardset.hazardtype
        type_settings = self.settings["hazard_types"][hazardtype.mnemonic]
        preprocessed = "values" in type_settings

        if len(hazardset.regions) == 0:
            return "No associated regions"

        layers = []
        if preprocessed:
            if len(hazardset.layers) == 0:
                return "No layer found"
            layers.append(hazardset.layers[0])
        else:
            for level in ("LOW", "MED", "HIG"):
                layer = hazardset.layer_by_level(level)
                if layer is None:
                    return "No layer for level {}".format(level)

                layers.append(layer)
            if "mask_return_period" in type_settings:
                layer = (
                    self.dbsession.query(Layer)
                    .filter(Layer.hazardset_id == hazardset_id)
                    .filter(Layer.mask.is_(True))
                )
                if layer.count() == 0:
                    return "Missing mask layer"
                layers.append(layer.one())

        affine = None
        shape = None
        for layer in layers:
            if not layer.downloaded:
                return "No data for layer {}".format(layer.name())
            try:
                with rasterio.Env():
                    with rasterio.open(self.layer_path(layer)) as reader:
                        bounds = reader.bounds
                        if bounds.bottom > bounds.top:
                            return "bounds.bottom > bounds.top"
                        if affine is None:
                            affine = reader.affine
                            shape = reader.shape
                        else:
                            if reader.affine != affine or reader.shape != shape:
                                return (
                                    "All layers should have the same origin,"
                                    " resolution and size"
                                )
            except:
                logger.error(
                    "Layer {} - Error opening file {}".format(
                        layer.name(), self.layer_path(layer)
                    ),
                    exc_info=True,
                )
                return "Error opening layer {}".format(layer.name())

        stats = (
            self.dbsession.query(
                Layer.local,
                func.min(Layer.data_lastupdated_date),
                func.min(Layer.metadata_lastupdated_date),
                func.min(Layer.calculation_method_quality),
                func.min(Layer.scientific_quality),
            )
            .filter(Layer.hazardset_id == hazardset.id)
            .filter(Layer.mask.isnot(True))
            .group_by(Layer.local)
        )

        if stats.count() > 1:
            return "Mixed local and global layers"

        stat = stats.one()

        hazardset.local = stat[0]
        hazardset.data_lastupdated_date = stat[1]
        hazardset.metadata_lastupdated_date = stat[2]
        hazardset.calculation_method_quality = stat[3]
        hazardset.scientific_quality = stat[4]
        hazardset.complete = True
        hazardset.complete_error = None
        self.dbsession.flush()

        logger.info("  Completed")
        return True
