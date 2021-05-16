#!/usr/bin/env python3
#
# Copyright (c) 2019 Roberto Riggio
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the License for the
# specific language governing permissions and limitations
# under the License.

"""RNIS Manager."""

import json

from tornado.httpclient import AsyncHTTPClient

from empower_core.serialize import serialize
from empower_core.appworker import EVERY
from empower_core.service import EService
from empower_core.launcher import srv_or_die

from lightedge_rniservice_manager.managers.rnismanager.subscription \
    import Subscription
from lightedge_rniservice_manager.managers.rnismanager.subscriptionshandler \
    import SubscriptionsHandler
from lightedge_rniservice_manager.managers.rnismanager.subscriptionscallbackhandler import SubscriptionsCallbackHandler

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8888
DEFAULT_USER = "root"
DEFAULT_PWD = "root"

SUBSCRIPTIONS = {
    "MeasRepUeSubscription":
        "lightedge_rniservice_manager.workers.measrepue.measrepue"
}


class MECManager(EService):
    """MEC Microservice baseclass."""

    def __init__(self, context, service_id, every=EVERY, **kwargs):

        super().__init__(context=context, service_id=service_id, every=every,
                         **kwargs)

        self.mec_service_registry = "http://127.0.0.1:8887/api/v1/services"
        self.state = "UNREGISTERED"

    def to_dict(self):
        """Return JSON representation."""

        output = super().to_dict()

        output['mec_service'] = self.mec_service

        return output

    @property
    def mec_service(self):
        """Return subscriptions."""

        return {
            "serInstanceId": self.service_id,
            "serName": "Radio Network Information Service",
            "serCategory": {
                "href": "/rni/v2/",
                "id": "rni",
                "name": "Radio Network Information Service",
                "version": "2.0"
            },
            "version": "1.0",
            "state": "ACTIVE",
            "serializer": "JSON",
        }

    async def loop(self):
        """Periodic job."""

        response = await self.register_mec_service()

        if response.code == 201:
            self.state = "REGISTERED"
        else:
            self.state = "UNREGISTERED"

        self.log.info("Sending periodic keep-alive, response %u",
                      response.code)

    async def register_mec_service(self):
        """Register MEC service."""

        http_client = AsyncHTTPClient()

        url = self.mec_service_registry + "/" + str(self.service_id)
        body = serialize(self.mec_service)

        response = await http_client.fetch(url, method='POST',
                                           body=json.dumps(body),
                                           raise_error=False)

        return response


class RNISManager(MECManager):
    """Service exposing the RNI service

    Parameters:
        ctrl_host: sd-ran controller host (optional, default: 127.0.0.1)
        ctrl_host: sd-ran controller port (optional, default: 8888)
    """

    HANDLERS = [SubscriptionsHandler, SubscriptionsCallbackHandler]

    def __init__(self, context, service_id, ctrl_host, ctrl_port,
                 ctrl_user, ctrl_pwd, every=EVERY):

        super().__init__(context=context, service_id=service_id,
                         ctrl_host=ctrl_host, ctrl_port=ctrl_port,
                         ctrl_user=ctrl_user, ctrl_pwd=ctrl_pwd,
                         every=every)

    @property
    def empower_url(self):
        """Return empower URL."""

        params = (self.ctrl_user, self.ctrl_pwd, self.ctrl_host,
                  self.ctrl_port)

        return "http://%s:%s@%s:%u/api/v1" % params

    async def get(self, url):
        """REST get method."""

        http_client = AsyncHTTPClient()
        response = await http_client.fetch(self.empower_url + url,
                                           raise_error=False)

        return response

    async def post(self, url, data):
        """Test post method."""

        data["version"] = "1.0"

        http_client = AsyncHTTPClient()

        response = await http_client.fetch(self.empower_url + url,
                                           method='POST',
                                           body=json.dumps(data),
                                           raise_error=False)

        return response

    @property
    def subscriptions(self):
        """Return subscriptions."""

        subscriptions = {}

        for service in srv_or_die("envmanager").env.services.values():

            if not isinstance(service, Subscription):
                continue

            subscriptions[service.service_id] = service

        return subscriptions

    def get_subscriptions_links(self):
        """Return subscriptions."""

        out = {
            "_links": {
                "self": "/rni/v2/subscriptions",
                "subscription": []
            }
        }

        for sub in self.subscriptions.values():

            to_add = {
                "href": "/rni/v2/subscriptions/%s" % sub.service_id,
                "subscriptionType": sub.SUB_CONFIG
            }

            out["_links"]["subscription"].append(to_add)

        return out

    def add_subscription(self, sub_id, params):
        """Add a new subscription."""

        if sub_id in self.subscriptions:
            raise ValueError("Subscription %s already defined" % sub_id)

        name = SUBSCRIPTIONS[params['subscriptionType']]

        params = {
            "subscription": params
        }

        env = srv_or_die("envmanager").env
        sub = env.register_service(name=name,
                                   params=params,
                                   service_id=sub_id)

        sub.add_callback(sub.callback_reference, callback_type="rest")

        return sub

    def rem_subscription(self, sub_id=None):
        """Remove subscription."""

        env = srv_or_die("envmanager").env

        if sub_id:
            service_id = self.subscriptions[sub_id].service_id
            env.unregister_service(service_id=service_id)
        else:
            for service_id in self.subscriptions:
                env.unregister_service(service_id=service_id)

    @property
    def ctrl_host(self):
        """Return ctrl_host."""

        return self.params["ctrl_host"]

    @ctrl_host.setter
    def ctrl_host(self, value):
        """Set ctrl_host."""

        if "ctrl_host" in self.params and self.params["ctrl_host"]:
            raise ValueError("Param ctrl_host can not be changed")

        self.params["ctrl_host"] = str(value)

    @property
    def ctrl_port(self):
        """Return ctrl_port."""

        return self.params["ctrl_port"]

    @ctrl_port.setter
    def ctrl_port(self, value):
        """Set ctrl_port."""

        if "ctrl_port" in self.params and self.params["ctrl_port"]:
            raise ValueError("Param ctrl_port can not be changed")

        self.params["ctrl_port"] = int(value)

    @property
    def ctrl_user(self):
        """Return ctrl_user."""

        return self.params["ctrl_user"]

    @ctrl_user.setter
    def ctrl_user(self, value):
        """Set ctrl_user."""

        if "ctrl_user" in self.params and self.params["ctrl_user"]:
            raise ValueError("Param ctrl_user can not be changed")

        self.params["ctrl_user"] = value

    @property
    def ctrl_pwd(self):
        """Return ctrl_pwd."""

        return self.params["ctrl_pwd"]

    @ctrl_pwd.setter
    def ctrl_pwd(self, value):
        """Set ctrl_pwd."""

        if "ctrl_pwd" in self.params and self.params["ctrl_pwd"]:
            raise ValueError("Param ctrl_pwd can not be changed")

        self.params["ctrl_pwd"] = value


def launch(context, service_id, ctrl_host=DEFAULT_HOST,
           ctrl_port=DEFAULT_PORT, ctrl_user=DEFAULT_USER,
           ctrl_pwd=DEFAULT_PWD, every=EVERY):
    """ Initialize the module. """

    return RNISManager(context, service_id, ctrl_host, ctrl_port, ctrl_user,
                       ctrl_pwd, every)
