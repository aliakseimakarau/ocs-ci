import logging
import time

from ocs_ci.framework import config
from ocs_ci.ocs import constants
from ocs_ci.ocs.exceptions import UnexpectedBehaviour
# from ocs_ci.ocs.node import wait_for_nodes_status, get_worker_nodes, get_master_nodes
# from ocs_ci.ocs.ocp import wait_for_cluster_connectivity
from ocs_ci.utility.utils import TimeoutSampler, exec_cmd
from ocs_ci.utility.utils import get_ocp_version
from ocs_ci.utility.service import KubeletService

logger = logging.getLogger(__name__)


class ZNodes(object):
    """
    Wrapper for ZNodes
    """

    def __init__(self):
        """
        Class Initialization.
        Run lsmod command to prepare isKVM variable.
        Also, get a reference for KubeletService object.
        """
        cmd = "sudo /usr/sbin/lsmod"
        result = exec_cmd(cmd)
        if b"kvm" in result.stdout.lower():
            self.isKVM = True
        else:
            self.isKVM = False

        if "bastion_ip" in config.ENV_DATA:
            self.isKVM = False

        logger.info(f"iskvm check: {self.isKVM}")

        self.service = KubeletService()

    def iskvm(self):
        """
        Verify if this environment is libvirt or kvm.

        Returns:
            bool: True if this is kvm environment, False otherwise
        """
        return self.isKVM

    def verify_machine_is_down(self, node):
        """
        Verify if ZNode is completely powered off

        Args:
            node (object): Node objects

        Returns:
            bool: True if machine is down, False otherwise

        """
        result = exec_cmd(
            "sudo virsh domstate test-ocp" + get_ocp_version("-") + f"-{node.name}"
        )
        if result.stdout.lower().rstrip() == b"running":
            return False
        else:
            return True

    def stop_znodes_machines(
        self, znode_machines, timeout=900, wait=True, force=True
    ):
        """
        Stop ZNode Machines

        Args:
            znode_machines (list): ZNode objects
            timeout (int): time in seconds to wait for node to reach 'not ready' state
            wait (bool): True if need to wait till the restarted node reaches timeout
                - for future use
            force (bool): True for ZNode ungraceful power off, False for
                graceful ZNode shutdown - for future use

        Raises:
            UnexpectedBehaviour: If ZNode machine is still up

        """
        for znode in znode_machines:
            self.service.stop(znode, timeout)

        # Wait for an additional 300+60 seconds (for pods to drain)
        waiting_time = 360
        logger.info(f"Waiting for {waiting_time} seconds")
        time.sleep(waiting_time)

    def stop_znodes_machines_kvm(
        self, znode_machines, timeout=900, wait=True, force=True
    ):
        """
        Stop ZNode Machines

        Args:
            znode_machines (list): ZNode objects
            timeout (int): time in seconds to wait for node to reach 'not ready' state
            wait (bool): True if need to wait till the restarted node reaches timeout
                - for future use
            force (bool): True for ZNode ungraceful power off, False for
                graceful ZNode shutdown - for future use

        Raises:
            UnexpectedBehaviour: If ZNode machine is still up

        """
        ocpversion = get_ocp_version("-")
        for node in znode_machines:
            cmd = f"sudo virsh shutdown test-ocp{ocpversion}-{node.name}"
            result = exec_cmd(cmd)
            logger.info(f"Result of shutdown {result}")
            logger.info("Verifying node is down")
            ret = TimeoutSampler(
                timeout=timeout,
                sleep=3,
                func=self.verify_machine_is_down,
                node=node,
            )
            logger.info(ret)
            if not ret.wait_for_func_status(result=True):
                raise UnexpectedBehaviour("Node {node.name} is still Running")

    def start_znodes_machines(
        self, znode_machines, timeout=900, wait=True
    ):
        # """
        # Start ZNode Machines

        # Args:
        #     znode_machines (list): List of ZNode machines
        #     timeout (int): time in seconds to wait for node to reach 'not ready' state,
        #         and 'ready' state.
        #     wait (bool): Wait for ZNodes to start - for future use
        # """
        for znode in znode_machines:
            self.service.start(znode, timeout)

    def start_znodes_machines_kvm(
        self, znode_machines, timeout=900, wait=True, force=True
    ):
        """
        Start ZNode Machines

        Args:
            znode_machines (list): List of ZNode machines
            timeout (int): time in seconds to wait for node to reach 'not ready' state,
                and 'ready' state.
            wait (bool): Wait for ZNodes to start - for future use
            force (bool): True for ZNode ungraceful power off, False for
                graceful ZNode shutdown - for future use
        """
        ocpversion = get_ocp_version("-")
        for node in znode_machines:
            result = exec_cmd(f"sudo virsh start test-ocp{ocpversion}-{node.name}")
            logger.info(f"Result of shutdown {result}")

        wait_for_cluster_connectivity(tries=900)
        wait_for_nodes_status(
            node_names=get_master_nodes(), status=constants.NODE_READY, timeout=timeout
        )
        wait_for_nodes_status(
            node_names=get_worker_nodes(), status=constants.NODE_READY, timeout=timeout
        )

    def restart_znodes_machines(self, znode_machines, timeout, wait):
        """
        Restart ZNode Machines

        Args:
            znode_machines (list): ZNode objects
            timeout (int): time in seconds to wait for node to reach 'not ready' state,
                and 'ready' state.
            wait (bool): True if need to wait till the restarted node reaches timeout
        """
        self.restart_znodes_machines(znode_machines, timeout, wait)
        self.start_znodes_machines(znode_machines, timeout, wait)

    def restart_znodes_machines_kvm(
        self, znode_machines, timeout, wait, force=True
    ):
        """
        Restart ZNode Machines

        Args:
            znode_machines (list): ZNode objects
            timeout (int): time in seconds to wait for node to reach 'not ready' state,
                and 'ready' state.
            wait (bool): True if need to wait till the restarted node reaches timeout
            force (bool): True for ZNode ungraceful power off, False for
                graceful ZNode shutdown - for future use
        """
        self.stop_znodes_machines_kvm(znode_machines, timeout, wait, force=force)
        self.start_znodes_machines_kvm(znode_machines, timeout, wait, force=force)
