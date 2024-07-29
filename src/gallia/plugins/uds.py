from gallia.commands import IOCBIPrimitive, SendPDUPrimitive
from gallia.commands.discover.doip import DoIPDiscoverer, DoIPDiscovererConfig
from gallia.commands.discover.find_xcp import (
    CanFindXCPConfig,
    FindXCP,
    TcpFindXCPConfig,
    UdpFindXCPConfig,
)
from gallia.commands.discover.uds.isotp import IsotpDiscoverer, IsotpDiscovererConfig
from gallia.commands.fuzz.uds.pdu import PDUFuzzer, PDUFuzzerConfig
from gallia.commands.primitive.generic.pdu import GenericPDUPrimitive, GenericPDUPrimitiveConfig
from gallia.commands.primitive.uds.dtc import (
    ClearDTCPrimitiveConfig,
    ControlDTCPrimitiveConfig,
    DTCPrimitive,
    ReadDTCPrimitiveConfig,
)
from gallia.commands.primitive.uds.ecu_reset import ECUResetPrimitive, ECUResetPrimitiveConfig
from gallia.commands.primitive.uds.iocbi import IOCBIPrimitiveConfig
from gallia.commands.primitive.uds.pdu import SendPDUPrimitiveConfig
from gallia.commands.primitive.uds.ping import PingPrimitive, PingPrimitiveConfig
from gallia.commands.primitive.uds.rdbi import (
    ReadByIdentifierPrimitive,
    ReadByIdentifierPrimitiveConfig,
)
from gallia.commands.primitive.uds.rmba import RMBAPrimitive, RMBAPrimitiveConfig
from gallia.commands.primitive.uds.rtcl import RTCLPrimitive, RTCLPrimitiveConfig
from gallia.commands.primitive.uds.vin import VINPrimitive, VINPrimitiveConfig
from gallia.commands.primitive.uds.wdbi import (
    WriteByIdentifierPrimitive,
    WriteByIdentifierPrimitiveConfig,
)
from gallia.commands.primitive.uds.wmba import WMBAPrimitive, WMBAPrimitiveConfig
from gallia.commands.primitive.uds.xcp import SimpleTestXCP, SimpleTestXCPConfig
from gallia.commands.scan.uds.identifiers import ScanIdentifiers, ScanIdentifiersConfig
from gallia.commands.scan.uds.memory import MemoryFunctionsScanner, MemoryFunctionsScannerConfig
from gallia.commands.scan.uds.reset import ResetScanner, ResetScannerConfig
from gallia.commands.scan.uds.sa_dump_seeds import SASeedsDumper, SASeedsDumperConfig
from gallia.commands.scan.uds.services import ServicesScanner, ServicesScannerConfig
from gallia.commands.scan.uds.sessions import SessionsScanner, SessionsScannerConfig
from gallia.commands.script.vecu import DbVirtualECUConfig, RngVirtualECUConfig, VirtualECU
from gallia.plugins.plugin import Command, CommandTree, Plugin
from gallia.services.uds import ECU
from gallia.transports import BaseTransport, registry


class UDSPlugin(Plugin):
    @classmethod
    def name(cls) -> str:
        return "Gallia UDS"

    @classmethod
    def description(cls) -> str:
        return "Default Gallia plugin for Unified Diagnostic Services (UDS) functionality"

    @classmethod
    def transports(cls) -> list[type[BaseTransport]]:
        return registry

    @classmethod
    def ecus(cls) -> list[type[ECU]]:
        return [ECU]

    @classmethod
    def commands(cls) -> dict[str, CommandTree | Command]:
        return {
            "discover": CommandTree(
                description="discover scanners for hosts and endpoints",
                subtree={
                    "uds": CommandTree(
                        description="Universal Diagnostic Services",
                        subtree={
                            "isotp": Command(
                                description="ISO-TP enumeration scanner",
                                config=IsotpDiscovererConfig,
                                command=IsotpDiscoverer,
                            )
                        },
                    ),
                    "doip": Command(
                        description="zero-knowledge DoIP enumeration scanner",
                        config=DoIPDiscovererConfig,
                        command=DoIPDiscoverer,
                    ),
                    "xcp": CommandTree(
                        description="XCP enumeration scanner",
                        subtree={
                            "can": Command(
                                description="XCP enumeration scanner for CAN",
                                config=CanFindXCPConfig,
                                command=FindXCP,
                            ),
                            "tcp": Command(
                                description="TCP enumeration scanner for CAN",
                                config=TcpFindXCPConfig,
                                command=FindXCP,
                            ),
                            "udp": Command(
                                description="UDP enumeration scanner for CAN",
                                config=UdpFindXCPConfig,
                                command=FindXCP,
                            ),
                        },
                    ),
                },
            ),
            "primitive": CommandTree(
                description="protocol specific primitives",
                subtree={
                    "uds": CommandTree(
                        description="Universal Diagnostic Services",
                        subtree={
                            "rdbi": Command(
                                description="ReadDataByIdentifier",
                                config=ReadByIdentifierPrimitiveConfig,
                                command=ReadByIdentifierPrimitive,
                            ),
                            "dtc": CommandTree(
                                description="DiagnosticTroubleCodes",
                                subtree={
                                    "clear": Command(
                                        description="Clear the DTCs using the ClearDiagnosticInformation service",
                                        config=ClearDTCPrimitiveConfig,
                                        command=DTCPrimitive,
                                    ),
                                    "control": Command(
                                        description="Stop or resume the setting of DTCs using the "
                                        "ControlDTCSetting service",
                                        config=ControlDTCPrimitiveConfig,
                                        command=DTCPrimitive,
                                    ),
                                    "read": Command(
                                        description="Read the DTCs using the ReadDTCInformation service",
                                        config=ReadDTCPrimitiveConfig,
                                        command=DTCPrimitive,
                                    ),
                                },
                            ),
                            "ecu-reset": Command(
                                description="ECUReset",
                                config=ECUResetPrimitiveConfig,
                                command=ECUResetPrimitive,
                            ),
                            "vin": Command(
                                description="request VIN",
                                config=VINPrimitiveConfig,
                                command=VINPrimitive,
                            ),
                            "iocbi": Command(
                                description="InputOutputControl",
                                config=IOCBIPrimitiveConfig,
                                command=IOCBIPrimitive,
                            ),
                            "ping": Command(
                                description="ping ECU via TesterPresent",
                                config=PingPrimitiveConfig,
                                command=PingPrimitive,
                            ),
                            "rmba": Command(
                                description="ReadMemoryByAddress",
                                config=RMBAPrimitiveConfig,
                                command=RMBAPrimitive,
                            ),
                            "rtcl": Command(
                                description="RoutineControl",
                                config=RTCLPrimitiveConfig,
                                command=RTCLPrimitive,
                            ),
                            "pdu": Command(
                                description="send a plain PDU",
                                config=SendPDUPrimitiveConfig,
                                command=SendPDUPrimitive,
                            ),
                            "wmba": Command(
                                description="WriteMemoryByAddress",
                                config=WMBAPrimitiveConfig,
                                command=WMBAPrimitive,
                            ),
                            "wdbi": Command(
                                description="WriteDataByIdentifier",
                                config=WriteByIdentifierPrimitiveConfig,
                                command=WriteByIdentifierPrimitive,
                            ),
                        },
                    ),
                    "generic": CommandTree(
                        description="generic networks primitives",
                        subtree={
                            "pdu": Command(
                                description="send a plain PDU",
                                config=GenericPDUPrimitiveConfig,
                                command=GenericPDUPrimitive,
                            )
                        },
                    ),
                    "xcp": Command(
                        description="XCP tester",
                        config=SimpleTestXCPConfig,
                        command=SimpleTestXCP,
                    ),
                },
            ),
            "scan": CommandTree(
                description="scanners for network protocol parameters",
                subtree={
                    "uds": CommandTree(
                        description="Universal Diagnostic Services",
                        subtree={
                            "memory": Command(
                                description="scan services with direct memory access",
                                config=MemoryFunctionsScannerConfig,
                                command=MemoryFunctionsScanner,
                            ),
                            "reset": Command(
                                description="identifier scan in ECUReset",
                                config=ResetScannerConfig,
                                command=ResetScanner,
                            ),
                            "dump-seeds": Command(
                                description="dump security access seeds",
                                config=SASeedsDumperConfig,
                                command=SASeedsDumper,
                            ),
                            "identifiers": Command(
                                description="identifier scan of a UDS service",
                                config=ScanIdentifiersConfig,
                                command=ScanIdentifiers,
                            ),
                            "sessions": Command(
                                description="session scan on an ECU",
                                config=SessionsScannerConfig,
                                command=SessionsScanner,
                            ),
                            "services": Command(
                                description="service scan on an ECU",
                                config=ServicesScannerConfig,
                                command=ServicesScanner,
                            ),
                        },
                    )
                },
            ),
            "fuzz": CommandTree(
                description="fuzzing tools",
                subtree={
                    "uds": CommandTree(
                        description="Universal Diagnostic Services",
                        subtree={
                            "pdu": Command(
                                description="fuzz the UDS pdu of selected services",
                                config=PDUFuzzerConfig,
                                command=PDUFuzzer,
                            )
                        },
                    )
                },
            ),
            "script": CommandTree(
                description="miscellaneous helper scripts",
                subtree={
                    "vecu": CommandTree(
                        description="spawn a virtual UDS ECU",
                        subtree={
                            "db": Command(
                                description="Virtual ECU which mimics the behavior of an ECU according to logs in the database",
                                config=DbVirtualECUConfig,
                                command=VirtualECU,
                            ),
                            "rng": Command(
                                description="Virtual ECU with randomized behavior",
                                config=RngVirtualECUConfig,
                                command=VirtualECU,
                            ),
                        },
                    )
                },
            ),
        }
