import logging
import random
import simpy

from leaf.application import Application, SourceTask, ProcessingTask, SinkTask
from leaf.infrastructure import Node, Link, Infrastructure
from leaf.orchestrator import Orchestrator
from leaf.power import PowerModelNode, PowerModelLink, PowerMeter

RANDOM_SEED = 1

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s\t%(message)s')


def main():
    infrastructure = create_infrastructure()
    application = create_application(source_node=infrastructure.node("datacenter"),
                                     sink_node=infrastructure.node("userdevice"))#In this scenario the userdevice is
                                                                                # the storage device where the
                                                                                #access network will drop the video. Then
                                                                                # it will be played on a TV.
    orchestrator = SimpleOrchestrator(infrastructure)
    orchestrator.place(application)

    application_pm = PowerMeter(application, name="application_meter")
    datacenter_to_core_pm = PowerMeter([infrastructure.node("datacenter"), infrastructure.node("core")],
                                  name="datacenter_to_core_meter")
    core_to_access_pm =  PowerMeter([infrastructure.node("core"), infrastructure.node("access")],
                                  name="core_to_access_meter")
    access_to_userdevice_pm =  PowerMeter([infrastructure.node("access"), infrastructure.node("userdevice")],
                                  name="access_to_userdevice_pm")
    infrastructure_pm = PowerMeter(infrastructure, name="infrastructure_meter", measurement_interval=2)

    env = simpy.Environment()
    env.process(application_pm.run(env, delay=0.5))
    env.process(datacenter_to_core_pm.run(env))
    env.process(core_to_access_pm.run(env))
    env.process(access_to_userdevice_pm.run(env))
    env.process(infrastructure_pm.run(env))
    env.run(until=5)


def create_infrastructure():

    infrastructure = Infrastructure()
    datacenter = Node("datacenter",cu=1000, power_model=PowerModelNode(max_power=1.32, static_power=1.32))
    core = Node("core", cu=1000, power_model=PowerModelNode(max_power=1.5, static_power=1.9e-3)) #based of malmodin (2020)
    access = Node("access", cu=1000, power_model=PowerModelNode(max_power=5, static_power=0.02)) #based of malmodin (2020)
    userdevice = Node("userdevice", cu=10, power_model=PowerModelNode(max_power=10, static_power=1)) #values for a home router
    wan_link_up = Link(datacenter, core, latency=100, bandwidth=100, power_model=PowerModelLink(6000e-9))
    wan_link_up2 = Link(core, access, latency=100, bandwidth=100, power_model=PowerModelLink(6000e-9))
    wifi_link_up = Link(access, userdevice, latency=10, bandwidth=75, power_model=PowerModelLink(300e-9))

    infrastructure.add_link(wifi_link_up)
    infrastructure.add_link(wan_link_up)
    infrastructure.add_link(wan_link_up2)

    return infrastructure


def create_application(source_node: Node, sink_node: Node):
    application = Application()

    source_task = SourceTask(cu=0.1, bound_node=source_node)
    processing_task = ProcessingTask(cu=0)
    sink_task = SinkTask(cu=0.01, bound_node=sink_node)

    application.add_task(source_task)
    application.add_task(processing_task, incoming_data_flows=[(source_task, 10)])
    application.add_task(sink_task, incoming_data_flows=[(processing_task, 0.01)])

    return application


class SimpleOrchestrator(Orchestrator):
    def _processing_task_placement(self, processing_task: ProcessingTask, application: Application) -> Node:
        return self.infrastructure.node("datacenter")


if __name__ == '__main__':
    random.seed(RANDOM_SEED)
    main()


