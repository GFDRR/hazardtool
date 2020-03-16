
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 by the GFDRR / World Bank
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

from webob import Request
from urllib.parse import urlencode


class GoogleAnalytics:
    def __init__(self):
        # TODO : replace by 'UA-75358940-1'
        self.tracking_id = ''

    def hit(self, hit_type):
        params = {
            "v": "v1",
            "tid": self.tracking_id,
            "t": hit_type
        }
        payload = urlencode(params)
        r = Request.blank("https://www.google-analytics.com/collect?{}".format(payload))
        r.send()
        print(r)
