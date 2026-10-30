"""One fresh Gurobi W claim after exact-source public license requalification."""

from scripts import pyomo_gurobi_retry_contract as qualified
from scripts.mvp2_pyomo_h215_w import Campaign


class LicenseCampaign(Campaign):
    """Reuse the qualified engine and science with a distinct predecessor-bound claim."""

    def __init__(self):
        super().__init__("gurobi")
        self.operational_contract = qualified
        self.CLAIM = qualified.PRIVATE_CLAIM
        self.CASE = "pyomo_gurobi_h215_w_native8h_license_v2"
        self.ARCHIVE = "pyomo-gurobi-h215-w-native8h-license-v2-evidence.tar.gz"
        self.PROFILE = {
            **self.PROFILE,
            "status": "one_license_requalified_pyomo_gurobi_W_arm_requested_20261030",
        }
