# Port structure definitions for Logix hardware modules.
#
# Each entry in PORT_STRUCTURES maps (vendor, product_type, product_code) to a list
# of PortDef objects, one per physical port on that module type.
#
# PortDef fields:
#   port_id          -- the Port Id="N" attribute value in L5X
#   port_type        -- the Type="..." attribute (ICP, Ethernet, Flex, 5094, RhinoBP, HART)
#   upstream_fixed   -- when True, the upstream_port value is always used as-is (no parent_mod_port_id
#                       lookup). When False, upstream is determined dynamically by comparing
#                       port_id to parent_mod_port_id at serialisation time.
#   upstream_port    -- the static Upstream="true/false" value (used when upstream_fixed=True,
#                       or as the default direction when upstream_fixed=False)
#   address_mode     -- "slot"    → emit Address=_slot
#                       "zero"    → emit Address="0" (literal zero, e.g. RhinoBP bus root)
#                       "empty"   → emit Address="" (IP not stored in binary)
#                       "omit"    → omit the Address attribute entirely
#   bus_mode         -- "none"    → no Bus element
#                       "always"  → always emit <Bus/> (no Size attribute)
#                       "fixed:N" → always emit <Bus Size="N"/>
#                       "children" → emit <Bus Size=K/> where K = count of this module's children
#                                   that connect to this port; if zero, still emits <Bus Size="0"/>
#                       "children_or_empty" → emit <Bus/> when no children, <Bus Size=K/> when K>0

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class PortDef:
    port_id: int
    port_type: str
    upstream_fixed: bool
    upstream_port: bool
    address_mode: str   # "slot", "zero", "empty", "omit"
    bus_mode: str       # "none", "always", "fixed:N", "children"


# ---------------------------------------------------------------------------
# Port structure table keyed by (vendor, product_type, product_code)
# ---------------------------------------------------------------------------

PORT_STRUCTURES: Dict[Tuple[int, int, int], List[PortDef]] = {

    # --- ControlLogix CPUs with Ethernet (L83E, L84E, L85E) PT=14 ---
    #
    # Root CPU (MajorFault="true"):
    #   Port 1 ICP  Upstream=false  Bus Size=17 (chassis capacity)
    #   Port 2 Eth  Upstream=false  Bus (no size)
    #
    # Remote chassis CPU (MajorFault="false", ParentModPortId=2):
    #   Port 1 ICP  Upstream=false  Bus Size=17
    #   Port 2 Eth  Upstream=true   (no Bus)
    #
    # Port 1 is always downstream (Upstream=false, Bus); Port 2 upstream depends on
    # whether this is a root CPU.  upstream_fixed=False so parent_mod_port_id logic
    # applies to Port 2; Port 1 is always downstream.
    (1, 14, 166): [  # 1756-L83E
        PortDef(port_id=1, port_type="ICP",      upstream_fixed=True,  upstream_port=False, address_mode="slot",  bus_mode="fixed:17"),
        PortDef(port_id=2, port_type="Ethernet",  upstream_fixed=False, upstream_port=False, address_mode="omit",  bus_mode="always"),
    ],
    (1, 14, 167): [  # 1756-L84E
        PortDef(port_id=1, port_type="ICP",      upstream_fixed=True,  upstream_port=False, address_mode="slot",  bus_mode="fixed:17"),
        PortDef(port_id=2, port_type="Ethernet",  upstream_fixed=False, upstream_port=False, address_mode="omit",  bus_mode="always"),
    ],
    (1, 14, 168): [  # 1756-L85E
        PortDef(port_id=1, port_type="ICP",      upstream_fixed=True,  upstream_port=False, address_mode="slot",  bus_mode="fixed:17"),
        PortDef(port_id=2, port_type="Ethernet",  upstream_fixed=False, upstream_port=False, address_mode="omit",  bus_mode="always"),
    ],
    (1, 14, 92): [  # 1756-L82E (ControlLogix 5580) -- root CPU, ICP + integrated Ethernet,
        # same port structure as the L85E (Port 1 ICP downstream, Port 2 Ethernet).
        # Added so an L82E CPU (out of the built-in catalog) still gets a <Ports>
        # section instead of an empty <Ports/> (Studio: "Required property 'Port'
        # was missing").
        PortDef(port_id=1, port_type="ICP",      upstream_fixed=True,  upstream_port=False, address_mode="slot",  bus_mode="fixed:17"),
        PortDef(port_id=2, port_type="Ethernet",  upstream_fixed=False, upstream_port=False, address_mode="omit",  bus_mode="always"),
    ],

    # --- Older ControlLogix CPUs (no Ethernet port) PT=14 ---
    # 1756-L72, 1756-L73: only Port 1 ICP.
    # In this dataset, these only appear as remote CPUs (Upstream=true, no Bus).
    # They could theoretically be root CPUs (no Bus or Bus) but are always children here.
    (1, 14, 93): [  # 1756-L72
        PortDef(port_id=1, port_type="ICP", upstream_fixed=False, upstream_port=True, address_mode="slot", bus_mode="none"),
    ],
    (1, 14, 94): [  # 1756-L73
        PortDef(port_id=1, port_type="ICP", upstream_fixed=False, upstream_port=True, address_mode="slot", bus_mode="none"),
    ],

    # --- ControlLogix Ethernet bridges PT=12 ---
    #
    # Standard use (connected to backplane, ParentModPortId=1):
    #   Port 1 ICP  Upstream=true   Address=slot  (no Bus)
    #   Port 2 Eth  Upstream=false  Address=""     Bus (no size)
    #
    # Remote chassis bridge (connected via Ethernet, ParentModPortId=2):
    #   Port 1 ICP  Upstream=false  Address=slot  Bus (no size — chassis carrier)
    #   Port 2 Eth  Upstream=true   Address=""     (no Bus)
    #
    # Both ports use upstream_fixed=False (direction determined by parent_mod_port_id).
    # Bus on Port 1 depends on whether it has children (bus_mode="children").
    # Bus on Port 2 is always present when Port 2 is downstream (standard case).
    # Since bus_mode must be static per PortDef, we use a special mode for Port 1 and Port 2:
    #   Port 1 gets bus when it has children (children_or_empty emits Bus/> unconditionally
    #   when it has any children, Bus/> without size when 0 children).
    # We use "children_or_none" = emit Bus (no size) when children > 0, else no Bus.
    # For Port 2: always emit Bus when it's the downstream port. We use "always" and let
    # the upstream logic suppress Bus for upstream ports is handled in _build_ports_xml.
    #
    # Simplification: Port 1 uses bus_mode="children_or_none"; Port 2 uses bus_mode="always".
    # In _build_ports_xml, we suppress Bus for upstream ports.
    (1, 12, 166): [  # 1756-EN2T
        PortDef(port_id=1, port_type="ICP",      upstream_fixed=False, upstream_port=False, address_mode="slot",  bus_mode="children_or_none"),
        PortDef(port_id=2, port_type="Ethernet",  upstream_fixed=False, upstream_port=False, address_mode="empty", bus_mode="always"),
    ],
    (1, 12, 169): [  # 1756-EN2F
        PortDef(port_id=1, port_type="ICP",      upstream_fixed=False, upstream_port=False, address_mode="slot",  bus_mode="children_or_none"),
        PortDef(port_id=2, port_type="Ethernet",  upstream_fixed=False, upstream_port=False, address_mode="empty", bus_mode="always"),
    ],
    (1, 12, 258): [  # 1756-EN4TR
        PortDef(port_id=1, port_type="ICP",      upstream_fixed=False, upstream_port=False, address_mode="slot",  bus_mode="children_or_none"),
        PortDef(port_id=2, port_type="Ethernet",  upstream_fixed=False, upstream_port=False, address_mode="empty", bus_mode="always"),
    ],

    # --- 1794 Flex adapters PT=12 ---
    # Port 1 Flex downstream (Bus Size=8 fixed — physical Flex bus capacity).
    # Port 2 Ethernet upstream. IP not stored in binary.
    (1, 12, 90): [   # 1794-AENT
        PortDef(port_id=1, port_type="Flex",     upstream_fixed=True,  upstream_port=False, address_mode="omit",  bus_mode="fixed:8"),
        PortDef(port_id=2, port_type="Ethernet",  upstream_fixed=True,  upstream_port=True,  address_mode="empty", bus_mode="none"),
    ],
    (1, 12, 261): [  # 1794-AENTR
        PortDef(port_id=1, port_type="Flex",     upstream_fixed=True,  upstream_port=False, address_mode="omit",  bus_mode="fixed:8"),
        PortDef(port_id=2, port_type="Ethernet",  upstream_fixed=True,  upstream_port=True,  address_mode="empty", bus_mode="none"),
    ],

    # --- 5094 Ethernet adapter PT=12 ---
    # Port 1 5094-bus downstream (Bus Size=17 — default 5094 chassis capacity).
    # Port 2 Ethernet upstream. Address slot is stored (observed Address="0" in samples).
    (1, 12, 322): [  # 5094-AEN2TR/A
        PortDef(port_id=1, port_type="5094",     upstream_fixed=True,  upstream_port=False, address_mode="slot",  bus_mode="fixed:17"),
        PortDef(port_id=2, port_type="Ethernet",  upstream_fixed=True,  upstream_port=True,  address_mode="empty", bus_mode="none"),
    ],

    # --- 1794 Flex I/O modules PT=7/10/109 ---
    # Single port Flex, always upstream.
    (1, 7, 34):  [PortDef(port_id=1, port_type="Flex", upstream_fixed=True, upstream_port=True, address_mode="slot", bus_mode="none")],  # 1794-IB16/A
    (1, 7, 35):  [PortDef(port_id=1, port_type="Flex", upstream_fixed=True, upstream_port=True, address_mode="slot", bus_mode="none")],  # 1794-OB16/A
    (1, 7, 37):  [PortDef(port_id=1, port_type="Flex", upstream_fixed=True, upstream_port=True, address_mode="slot", bus_mode="none")],  # 1794-OW8/A
    (1, 7, 156): [PortDef(port_id=1, port_type="Flex", upstream_fixed=True, upstream_port=True, address_mode="slot", bus_mode="none")],  # 1794-IB32/A
    (1, 10, 25): [PortDef(port_id=1, port_type="Flex", upstream_fixed=True, upstream_port=True, address_mode="slot", bus_mode="none")],  # 1794-IE8/B
    (1, 10, 26): [PortDef(port_id=1, port_type="Flex", upstream_fixed=True, upstream_port=True, address_mode="slot", bus_mode="none")],  # 1794-OE4/B
    (1, 10, 153):[PortDef(port_id=1, port_type="Flex", upstream_fixed=True, upstream_port=True, address_mode="slot", bus_mode="none")],  # 1794-IF8IH/A
    (1, 10, 154):[PortDef(port_id=1, port_type="Flex", upstream_fixed=True, upstream_port=True, address_mode="slot", bus_mode="none")],  # 1794-OF8IH/A
    (1, 109, 6): [PortDef(port_id=1, port_type="Flex", upstream_fixed=True, upstream_port=True, address_mode="slot", bus_mode="none")],  # 1794-IP4/B

    # --- 5094 I/O modules PT=7/10/115 ---
    # 5094-IB16/A and 5094-OB16/A: single port 5094, upstream.
    # 5094-IF8IH/A and 5094-OF8IH/A: port 1 5094 upstream + port 2 HART downstream
    #   with Bus Size=8 (8 HART channels per module).
    (1, 7, 397):  [PortDef(port_id=1, port_type="5094", upstream_fixed=True, upstream_port=True, address_mode="slot", bus_mode="none")],  # 5094-IB16/A
    (1, 7, 399):  [PortDef(port_id=1, port_type="5094", upstream_fixed=True, upstream_port=True, address_mode="slot", bus_mode="none")],  # 5094-OB16/A
    (1, 115, 323): [  # 5094-IF8IH/A
        PortDef(port_id=1, port_type="5094", upstream_fixed=True,  upstream_port=True,  address_mode="slot", bus_mode="none"),
        PortDef(port_id=2, port_type="HART", upstream_fixed=True,  upstream_port=False, address_mode="omit", bus_mode="fixed:8"),
    ],
    (1, 115, 324): [  # 5094-OF8IH/A
        PortDef(port_id=1, port_type="5094", upstream_fixed=True,  upstream_port=True,  address_mode="slot", bus_mode="none"),
        PortDef(port_id=2, port_type="HART", upstream_fixed=True,  upstream_port=False, address_mode="omit", bus_mode="fixed:8"),
    ],

    # --- 1756 backplane I/O modules PT=7/10 ---
    # Single port ICP, always upstream.
    (1, 7, 11):  [PortDef(port_id=1, port_type="ICP", upstream_fixed=True, upstream_port=True, address_mode="slot", bus_mode="none")],  # 1756-IB16
    (1, 7, 30):  [PortDef(port_id=1, port_type="ICP", upstream_fixed=True, upstream_port=True, address_mode="slot", bus_mode="none")],  # 1756-OW16I
    (1, 10, 7):  [PortDef(port_id=1, port_type="ICP", upstream_fixed=True, upstream_port=True, address_mode="slot", bus_mode="none")],  # 1756-IF8/A

    # --- PowerFlex drives PT=123/142/143 ---
    # Port 1 RhinoBP downstream, Address=0 (literal zero — root of the RhinoBP bus).
    # Ethernet port upstream (port ID varies by model), IP not stored in binary.
    (1, 123, 1168): [  # PowerFlex 753-NET-E
        PortDef(port_id=1, port_type="RhinoBP",  upstream_fixed=True, upstream_port=False, address_mode="zero",  bus_mode="always"),
        PortDef(port_id=2, port_type="Ethernet",  upstream_fixed=True, upstream_port=True,  address_mode="empty", bus_mode="none"),
    ],
    (1, 142, 1168): [  # PowerFlex 753-ENETR
        PortDef(port_id=1, port_type="RhinoBP",  upstream_fixed=True, upstream_port=False, address_mode="zero",  bus_mode="always"),
        PortDef(port_id=5, port_type="Ethernet",  upstream_fixed=True, upstream_port=True,  address_mode="empty", bus_mode="none"),
    ],
    (1, 143, 2192): [  # PowerFlex 755-EENET
        PortDef(port_id=1,  port_type="RhinoBP",  upstream_fixed=True, upstream_port=False, address_mode="zero",  bus_mode="always"),
        PortDef(port_id=13, port_type="Ethernet",  upstream_fixed=True, upstream_port=True,  address_mode="empty", bus_mode="none"),
    ],

    # --- Drive peripheral expansion cards PT=0, PC=28 ---
    # Only Port 2 RhinoBP, always upstream (connects back to drive's RhinoBP bus).
    # Address = the module's slot on the RhinoBP bus.
    (1, 0, 28): [  # RHINOBP-DRIVE-PERIPHERAL-MODULE
        PortDef(port_id=2, port_type="RhinoBP", upstream_fixed=True, upstream_port=True, address_mode="slot", bus_mode="none"),
    ],

    # --- Generic Ethernet module PT=0, PC=18 ---
    # Only Port 2 Ethernet, upstream. IP not stored in binary.
    (1, 0, 18): [  # ETHERNET-MODULE
        PortDef(port_id=2, port_type="Ethernet", upstream_fixed=True, upstream_port=True, address_mode="empty", bus_mode="none"),
    ],

    # --- Endress+Hauser flow meters V=1182 ---
    # All have a single Ethernet port that is always upstream.
    # IP address not stored in binary.
    (1182, 0, 4162):  [PortDef(port_id=1, port_type="Ethernet", upstream_fixed=True, upstream_port=True, address_mode="empty", bus_mode="none")],  # Promag_53/A
    (1182, 0, 4177):  [PortDef(port_id=1, port_type="Ethernet", upstream_fixed=True, upstream_port=True, address_mode="empty", bus_mode="none")],  # Promass_83/A
    (1182, 43, 4154): [PortDef(port_id=1, port_type="Ethernet", upstream_fixed=True, upstream_port=True, address_mode="empty", bus_mode="none")],  # Promag_100
    (1182, 43, 4155): [PortDef(port_id=1, port_type="Ethernet", upstream_fixed=True, upstream_port=True, address_mode="empty", bus_mode="none")],  # Promass_300_500
    (1182, 43, 4156): [PortDef(port_id=1, port_type="Ethernet", upstream_fixed=True, upstream_port=True, address_mode="empty", bus_mode="none")],  # Promag_300_500
    (1182, 43, 4170): [PortDef(port_id=1, port_type="Ethernet", upstream_fixed=True, upstream_port=True, address_mode="empty", bus_mode="none")],  # Promass_100

    # --- Third-party Ethernet devices (V=322, e.g. Bihl+Wiedemann ASI gateway) ---
    (322, 12, 1422): [PortDef(port_id=2, port_type="Ethernet", upstream_fixed=True, upstream_port=True, address_mode="empty", bus_mode="none")],
}
