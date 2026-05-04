import math as m


MU = 4 * (10**14)
EARTH_RADIUS_M = 6_371_000
EARTH_RADIUS_KM = EARTH_RADIUS_M / 1000


fuelDensity = {
    "RP-1": 810, # kg/m^3
    "LH2": 70, # kg/m^3
    "LCH4": 422, # kg/m^3
    "MMH": 880, # kg/m^3
}

oxiderDensity = {
    "LOX": 1141, # kg/m^3
    "N2O4": 1440, # kg/m^3
}


def calculateVelocity(radius: float, a: float):
    velocity = m.sqrt(MU * (2 / radius - 1 / a))
    return velocity


def calculateDeltaVHoman(initialOrbitRadius: float, targetOrbitRadius: float):
    initialVelocity = calculateVelocity(initialOrbitRadius, initialOrbitRadius)
    targetVelocity = calculateVelocity(targetOrbitRadius, targetOrbitRadius)
    transferOrbitPerigeeVelocity = calculateVelocity(
        initialOrbitRadius,
        (targetOrbitRadius + initialOrbitRadius) / 2,
    )
    transferOrbitApogeeVelocity = calculateVelocity(
        targetOrbitRadius,
        (targetOrbitRadius + initialOrbitRadius) / 2,
    )
    deltaV = abs(transferOrbitPerigeeVelocity - initialVelocity) + abs(
        transferOrbitApogeeVelocity - targetVelocity
    )
    firstBurnVelocity = abs(transferOrbitPerigeeVelocity - initialVelocity)
    secondBurnVelocity = abs(transferOrbitApogeeVelocity - targetVelocity)
    return (deltaV, firstBurnVelocity, secondBurnVelocity)


def calculateTravelTime(a, mu):
    travelTime = m.pi*m.sqrt(a**3/mu)
    return travelTime


def calculateMassRatio(deltaV, specificImpulse):
    g0 = 9.81
    massRatio = m.exp(deltaV / (specificImpulse * g0))
    return massRatio


def calulateFuelMass(massRatio, payloadMass, constructionMassRatio, oxidezerFuelMassRatio):
    totalFuelMass = (payloadMass/(1/(massRatio - 1) - constructionMassRatio))
    fuelMass = totalFuelMass / (1 + oxidezerFuelMassRatio)
    oxidizerMass = totalFuelMass - fuelMass
    return (totalFuelMass, fuelMass, oxidizerMass)


def calculateRequiredTankVolume(liquidMass, fuelType, oxidizerType, gasCashionRatio):
    fuelDensityValue = fuelDensity.get(fuelType, 0)
    oxidizerDensityValue = oxiderDensity.get(oxidizerType, 0)
    fuelVolume = liquidMass / fuelDensityValue
    if oxidizerDensityValue == 0:
        oxidezerVolume = 0
        return oxidezerVolume
    else:
        oxidizerVolume = liquidMass / oxidizerDensityValue
    fuelTankVolume = fuelVolume * (1 + gasCashionRatio)
    oxidizerTankVolume = oxidizerVolume * (1 + gasCashionRatio)
    if fuelDensityValue == 0 or oxidizerDensityValue == 0:
        raise ValueError("Invalid fuel or oxidizer type provided.")
    return fuelTankVolume, oxidizerTankVolume


def calculateStagePropellantFromDeltaV(deltaV, specificImpulse, payloadMass, constructionMassRatio, oxidezerFuelMassRatio):
    massRatio = calculateMassRatio(deltaV, specificImpulse)
    totalFuelMass, fuelMass, oxidizerMass = calulateFuelMass(
        massRatio,
        payloadMass,
        constructionMassRatio,
        oxidezerFuelMassRatio,
    )
    return massRatio, totalFuelMass, fuelMass, oxidizerMass


def calculateUniversalStageForFullStack(deltaV, specificImpulse, payloadMass, constructionMassRatio, oxidezerFuelMassRatio, max_iterations=100, tolerance=1e-6):
    stageMassEstimate = 0.0
    for _ in range(max_iterations):
        massRatio, totalFuelMass, fuelMass, oxidizerMass = calculateStagePropellantFromDeltaV(
            deltaV,
            specificImpulse,
            payloadMass + stageMassEstimate,
            constructionMassRatio,
            oxidezerFuelMassRatio,
        )
        constructionMass = totalFuelMass * constructionMassRatio
        newStageMass = totalFuelMass + constructionMass
        if abs(newStageMass - stageMassEstimate) <= tolerance:
            return massRatio, totalFuelMass, fuelMass, oxidizerMass, newStageMass
        stageMassEstimate = newStageMass
    raise ValueError("Не удалось сойтись при расчете универсальной ступени.")


def buildStagesForHomanTransfer(payloadMass, specificImpulse, deltaV, firstBurnVelocity, secondBurnVelocity, constructionMassRatio, oxidezerFuelMassRatio, fuelType: str, oxidizerType: str, oxidezerTankType: str, fuelTankType: str, stageCount: int = 2, useUniversalStage: bool = False, useDocking: bool = False, stage1SpecificImpulse=None, stage2SpecificImpulse=None, universalSpecificImpulse=None, stage1ConstructionMassRatio=None, stage2ConstructionMassRatio=None, universalConstructionMassRatio=None, fuelTankMaterial='AMg6', oxidizerTankMaterial='AMg6'):
    """Builds the stages for a Homan transfer based on the provided parameters.
    stageCount: The number of stages for the transfer. If 2 is provided the first stage will be used for the first burn and the second stage for the second burn. If 1 is provided, a single stage will be used for both burns.
    fuelType: The type of fuel used in the stages. This will determine the need in screen vacuum thermal insulation and the tank design.
    useUniversalStage: If True, a single stage design will be used for both burns, regardless of the stageCount parameter. This is useful for simplifying the design and manufacturing process, but may result in suboptimal performance for one of the burns.
    """
    if stageCount not in [1, 2]:
        raise ValueError("Invalid stage count provided. Only 1 or 2 stages are supported.")
    if stageCount == 1:
        singleStageMassRatio, totalFuelMass, fuelMass, oxidizerMass = calculateStagePropellantFromDeltaV(
            deltaV,
            specificImpulse,
            payloadMass,
            constructionMassRatio,
            oxidezerFuelMassRatio,
        )
        stages = [
            stage(
                totalFuelMass,
                fuelMass,
                oxidizerMass,
                constructionMassRatio,
                fuelType,
                oxidizerType,
                oxidezerTankType,
                fuelTankType,
                fuelTankMaterial=fuelTankMaterial,
                oxidezerTankMaterial=oxidizerTankMaterial,
                stageNumber=1,
                payloadMass=payloadMass,
                dockingPort=False,
                assignedBurn="Оба включения",
                specificImpulse=specificImpulse,
                massRatio=singleStageMassRatio,
                requiredDeltaV=deltaV,
                displayName="Единая ступень",
            )
        ]
    elif useUniversalStage:
        universalIsp = universalSpecificImpulse if universalSpecificImpulse is not None else specificImpulse
        universalConstructionRatio = universalConstructionMassRatio if universalConstructionMassRatio is not None else constructionMassRatio
        governingDeltaV = max(firstBurnVelocity, secondBurnVelocity)
        universalMassRatio, stageTotalFuelMass, stageFuelMass, stageOxidizerMass, universalStageMass = calculateUniversalStageForFullStack(
            governingDeltaV,
            universalIsp,
            payloadMass,
            universalConstructionRatio,
            oxidezerFuelMassRatio,
        )
        firstStage = stage(
            stageTotalFuelMass,
            stageFuelMass,
            stageOxidizerMass,
            universalConstructionRatio,
            fuelType,
            oxidizerType,
            oxidezerTankType,
            fuelTankType,
            fuelTankMaterial=fuelTankMaterial,
            oxidezerTankMaterial=oxidizerTankMaterial,
            stageNumber=1,
            payloadMass=payloadMass + universalStageMass,
            dockingPort=useDocking,
            assignedBurn="Первое включение",
            specificImpulse=universalIsp,
            massRatio=universalMassRatio,
            requiredDeltaV=firstBurnVelocity,
            displayName="Универсальная ступень 1" if not useDocking else "Стыкуемая ступень 1",
        )
        secondStage = stage(
            stageTotalFuelMass,
            stageFuelMass,
            stageOxidizerMass,
            universalConstructionRatio,
            fuelType,
            oxidizerType,
            oxidezerTankType,
            fuelTankType,
            fuelTankMaterial=fuelTankMaterial,
            oxidezerTankMaterial=oxidizerTankMaterial,
            stageNumber=2,
            payloadMass=payloadMass,
            dockingPort=useDocking,
            assignedBurn="Второе включение",
            specificImpulse=universalIsp,
            massRatio=universalMassRatio,
            requiredDeltaV=secondBurnVelocity,
            displayName="Универсальная ступень 2" if not useDocking else "Стыкуемая ступень 2",
        )
        stages = [firstStage, secondStage]
    else:
        firstStageIsp = stage1SpecificImpulse if stage1SpecificImpulse is not None else specificImpulse
        secondStageIsp = stage2SpecificImpulse if stage2SpecificImpulse is not None else specificImpulse
        firstStageConstructionRatio = stage1ConstructionMassRatio if stage1ConstructionMassRatio is not None else constructionMassRatio
        secondStageConstructionRatio = stage2ConstructionMassRatio if stage2ConstructionMassRatio is not None else constructionMassRatio

        _, totalFuelMass2, fuelMass2, oxidezerMass2 = calculateStagePropellantFromDeltaV(
            secondBurnVelocity,
            secondStageIsp,
            payloadMass,
            secondStageConstructionRatio,
            oxidezerFuelMassRatio,
        )
        secondStage = stage(
            totalFuelMass2,
            fuelMass2,
            oxidezerMass2,
            secondStageConstructionRatio,
            fuelType,
            oxidizerType,
            oxidezerTankType,
            fuelTankType,
            fuelTankMaterial=fuelTankMaterial,
            oxidezerTankMaterial=oxidizerTankMaterial,
            stageNumber=2,
            payloadMass=payloadMass,
            dockingPort=useDocking,
            assignedBurn="Второе включение",
            specificImpulse=secondStageIsp,
            massRatio=calculateMassRatio(secondBurnVelocity, secondStageIsp),
            requiredDeltaV=secondBurnVelocity,
            displayName="Стыкуемая ступень 2" if useDocking else "Ступень 2",
        )
        stage1PayloadMass = payloadMass + secondStage.totalStageMass
        _, totalFuelMass1, fuelMass1, oxidezerMass1 = calculateStagePropellantFromDeltaV(
            firstBurnVelocity,
            firstStageIsp,
            stage1PayloadMass,
            firstStageConstructionRatio,
            oxidezerFuelMassRatio,
        )
        firstStage = stage(
            totalFuelMass1,
            fuelMass1,
            oxidezerMass1,
            firstStageConstructionRatio,
            fuelType,
            oxidizerType,
            oxidezerTankType,
            fuelTankType,
            fuelTankMaterial=fuelTankMaterial,
            oxidezerTankMaterial=oxidizerTankMaterial,
            stageNumber=1,
            payloadMass=stage1PayloadMass,
            dockingPort=useDocking,
            assignedBurn="Первое включение",
            specificImpulse=firstStageIsp,
            massRatio=calculateMassRatio(firstBurnVelocity, firstStageIsp),
            requiredDeltaV=firstBurnVelocity,
            displayName="Стыкуемая ступень 1" if useDocking else "Ступень 1",
        )
        stages = [firstStage, secondStage]
    if useDocking:
        for currentStage in stages:
            if "стыковка" not in currentStage.assignedBurn.lower():
                currentStage.assignedBurn = f"{currentStage.assignedBurn} + стыковка"
    return stages


class stage:
    """A class representing a stage of the booster stage. It contains information about the fuel mass, oxidizer mass, construction mass, fuel type, tank types, and whether it has a docking port."""
    def __init__(self, totalFuelMass, fuelMass, oxidizerMass, constructionMassRatio, fuelType, oxidizerType, oxidezerTankType, fuelTankType, fuelTankMaterial='AMg6', oxidezerTankMaterial='AMg6', tanksThickness=0.01, stageNumber=1, payloadMass=0, dockingPort=False, assignedBurn="", specificImpulse=None, massRatio=None, requiredDeltaV=None, displayName=None):
        self.stageNumber = stageNumber
        self.payloadMass = payloadMass
        self.totalFuelMass = totalFuelMass
        self.fuelMass = fuelMass
        self.oxidizerMass = oxidizerMass
        self.constructionMass = totalFuelMass * constructionMassRatio
        self.fuelType = fuelType
        self.oxidizerType = oxidizerType
        self.oxidezerTankType = oxidezerTankType
        self.fuelTankType = fuelTankType
        self.fuelTankMaterial = fuelTankMaterial
        self.oxidezerTankMaterial = oxidezerTankMaterial
        self.RCSThruster = RCSThruster
        self.tanksThickness = tanksThickness
        self.tanksMass = 0 #Calculated for empty tanks using calculateTankVolume function and the tank types. This will depend on the fuel mass, oxidizer mass, and the specific tank designs for the given fuel and oxidizer.
        self.auxiliarySystems = [] #Placeholder for auxiliary systems such as pumps, valves, and control systems. The mass of these systems will depend on the specific design and requirements of the stage.
        self.tankMaterialDensity = {
            'AMg6': 1800, # kg/m^3
            'Aluminum': 2700, # kg/m^3
            'Titanium': 4500, # kg/m^3
            'CarbonFiber': 1600, # kg/m^3
        }
        self.dockingPort = dockingPort
        self.assignedBurn = assignedBurn
        self.specificImpulse = specificImpulse
        self.massRatio = massRatio
        self.requiredDeltaV = requiredDeltaV
        self.displayName = displayName or f"Ступень {stageNumber}"
        self.leftConstructionMass = self.constructionMass - self.tanksMass
        if self.dockingPort:
            self.advancedRCS = True #Advanced RCS is required for docking maneuvers. If enabled stage has eight RCS thrusters, otherwise it has two. Advanced RCS also allows for more precise control during maneuvers, which is crucial for docking operations.
            self.RCSThruster = RCSThruster(thrust=392, specificImpulse=302/9.81, propellantType="MMH", thrusterType="Bipropellant", thrusterMass=3, propellantMass=50, thrustersQuantity=8) #Placeholder values for RCS thruster parameters, this will depend on the specific design and requirements of the system.
            self.addAuxiliarySystems("Advanced RCS", self.RCSThruster.thrusterMass) #Placeholder mass for advanced RCS system, this will depend on the specific design and requirements of the system.
            self.addAuxiliarySystems("Docking Port", 100) #Placeholder mass for docking port, this will depend on the specific design and requirements of the system.
        else:
            self.advancedRCS = False
            self.RCSThruster = RCSThruster(thrust=392, specificImpulse=302/9.81, propellantType="MMH", thrusterType="Bipropellant", thrusterMass=3, propellantMass=50, thrustersQuantity=4)
            self.addAuxiliarySystems("RCS", self.RCSThruster.thrusterMass)
        self.totalStageMass = self.constructionMass + self.fuelMass + self.oxidizerMass


    def calculateTanksMass(self):
        fuelTankVolume = calculateRequiredTankVolume(self.fuelMass, self.fuelType, self.oxidizerType, gasCashionRatio=0.1)
        oxidizerTankVolume = calculateRequiredTankVolume(self.oxidizerMass, self.oxidizerType, self.fuelType, gasCashionRatio=0.1)
        if self.fuelTankType == "Spherical":
            fuelTankMass = (4/3) * self.tanksThickness * m.pi * (fuelTankVolume / (4/3 * m.pi))**(2/3) * self.tankMaterialDensity.get(self.fuelTankMaterial, 0)
        elif self.fuelTankType == "Cylindrical": #A tank with hemispherical ends is a common design for cylindrical tanks, as it provides a good balance between structural integrity and efficient use of space.
            fuelTankMass = (2 * m.pi * (fuelTankVolume / (m.pi * self.tanksThickness))**(1/2) * self.tanksThickness + 2 * m.pi * (fuelTankVolume / (m.pi * self.tanksThickness))**(1/2) * self.tanksThickness) * self.tankMaterialDensity.get(self.fuelTankMaterial, 0)
        elif self.fuelTankType == "Torus": #A toroidal tank is a doughnut-shaped tank that can be used to store propellant in a compact and efficient manner. The mass of a toroidal tank can be calculated using the formula: M = 2 * pi^2 * R * r * t * density, where R is the major radius, r is the minor radius, t is the thickness of the tank walls, and density is the density of the tank material.
            fuelTankMass = 2 * m.pi**2 * (fuelTankVolume / (2 * m.pi**2 * self.tanksThickness))**(1/2) * (fuelTankVolume / (2 * m.pi**2 * self.tanksThickness))**(1/2) * self.tanksThickness * self.tankMaterialDensity.get(self.fuelTankMaterial, 0)
        else:
            fuelTankMass = 0 # Placeholder value for fuel tank mass calculation, if an invalid tank type is provided.
        if self.oxidezerTankType == "Spherical":
            oxidizerTankMass = (4/3) * self.tanksThickness * m.pi * (oxidizerTankVolume / (4/3 * m.pi))**(2/3) * self.tankMaterialDensity.get(self.oxidezerTankMaterial, 0)
        elif self.oxidezerTankType == "Cylindrical": #A tank with hemispherical ends is a common design for cylindrical tanks, as it provides a good balance between structural integrity and efficient use of space.
            oxidizerTankMass = (2 * m.pi * (oxidizerTankVolume / (m.pi * self.tanksThickness))**(1/2) * self.tanksThickness + 2 * m.pi * (oxidizerTankVolume / (m.pi * self.tanksThickness))**(1/2) * self.tanksThickness) * self.tankMaterialDensity.get(self.oxidezerTankMaterial, 0)
        elif self.oxidezerTankType == "Torus": #A toroidal tank is a doughnut-shaped tank that can be used to store propellant in a compact and efficient manner. The mass of a toroidal tank can be calculated using the formula: M = 2 * pi^2 * R * r * t * density, where R is the major radius, r is the minor radius, t is the thickness of the tank walls, and density is the density of the tank material.
            oxidizerTankMass = 2 * m.pi**2 * (oxidizerTankVolume / (2 * m.pi**2 * self.tanksThickness))**(1/2) * (oxidizerTankVolume / (2 * m.pi**2 * self.tanksThickness))**(1/2) * self.tanksThickness * self.tankMaterialDensity.get(self.oxidezerTankMaterial, 0)
        else:
            oxidizerTankMass = 0 # Placeholder value for oxidizer tank mass calculation, if an invalid tank type is provided.
        self.tanksMass = fuelTankMass + oxidizerTankMass
        self.leftConstructionMass = self.constructionMass - self.tanksMass


    def addAuxiliarySystems(self, auxiliarySystemName, auxiliarySystemMass):
        self.auxiliarySystems.append((auxiliarySystemName, auxiliarySystemMass))
        if self.leftConstructionMass-auxiliarySystemMass < 0:
            raise ValueError("Auxiliary system mass exceeds the remaining construction mass for this stage.")
        else:
            self.leftConstructionMass -= auxiliarySystemMass


def summarizeStage(stageObject, gasCashionRatio=0.1):
    fuelTankVolume, _ = calculateRequiredTankVolume(
        stageObject.fuelMass,
        stageObject.fuelType,
        stageObject.oxidizerType,
        gasCashionRatio,
    )
    _, oxidizerTankVolume = calculateRequiredTankVolume(
        stageObject.oxidizerMass,
        stageObject.fuelType,
        stageObject.oxidizerType,
        gasCashionRatio,
    )
    return {
        "stage_number": stageObject.stageNumber,
        "name": stageObject.displayName,
        "assigned_burn": stageObject.assignedBurn,
        "payload_mass": stageObject.payloadMass,
        "total_propellant_mass": stageObject.totalFuelMass,
        "fuel_mass": stageObject.fuelMass,
        "oxidizer_mass": stageObject.oxidizerMass,
        "construction_mass": stageObject.constructionMass,
        "total_stage_mass": stageObject.totalStageMass,
        "fuel_tank_volume": fuelTankVolume,
        "oxidizer_tank_volume": oxidizerTankVolume,
        "fuel_tank_material": stageObject.fuelTankMaterial,
        "oxidizer_tank_material": stageObject.oxidezerTankMaterial,
        "specific_impulse": stageObject.specificImpulse,
        "mass_ratio": stageObject.massRatio,
        "required_delta_v": stageObject.requiredDeltaV,
        "docking_port": stageObject.dockingPort,
        "advanced_rcs": stageObject.advancedRCS,
        "auxiliary_systems": list(stageObject.auxiliarySystems),
        "remaining_construction_mass": stageObject.leftConstructionMass,
    }


def buildBoosterSummaryForHohmannTransfer(payloadMass, specificImpulse, deltaV, firstBurnVelocity, secondBurnVelocity, constructionMassRatio, oxidezerFuelMassRatio, fuelType: str, oxidizerType: str, oxidezerTankType: str, fuelTankType: str, stageCount: int = 2, useUniversalStage: bool = False, useDocking: bool = False, stage1SpecificImpulse=None, stage2SpecificImpulse=None, universalSpecificImpulse=None, stage1ConstructionMassRatio=None, stage2ConstructionMassRatio=None, universalConstructionMassRatio=None, gasCashionRatio=0.1, fuelTankMaterial='AMg6', oxidizerTankMaterial='AMg6', startMass=None, customAuxiliarySystems=None, boosterDiameter=None):
    stages = buildStagesForHomanTransfer(
        payloadMass,
        specificImpulse,
        deltaV,
        firstBurnVelocity,
        secondBurnVelocity,
        constructionMassRatio,
        oxidezerFuelMassRatio,
        fuelType,
        oxidizerType,
        oxidezerTankType,
        fuelTankType,
        stageCount=stageCount,
        useUniversalStage=useUniversalStage,
        useDocking=useDocking,
        stage1SpecificImpulse=stage1SpecificImpulse,
        stage2SpecificImpulse=stage2SpecificImpulse,
        universalSpecificImpulse=universalSpecificImpulse,
        stage1ConstructionMassRatio=stage1ConstructionMassRatio,
        stage2ConstructionMassRatio=stage2ConstructionMassRatio,
        universalConstructionMassRatio=universalConstructionMassRatio,
        fuelTankMaterial=fuelTankMaterial,
        oxidizerTankMaterial=oxidizerTankMaterial,
    )
    stageSummaries = [summarizeStage(item, gasCashionRatio=gasCashionRatio) for item in stages]
    existingAuxiliaryMass = sum(sum(mass for _name, mass in stage["auxiliary_systems"]) for stage in stageSummaries)
    customAuxiliarySystems = customAuxiliarySystems or []
    customAuxiliaryMass = sum(mass for _name, mass in customAuxiliarySystems)
    totalPropellantMass = sum(stage["total_propellant_mass"] for stage in stageSummaries)
    if not stageSummaries:
        totalInitialMass = payloadMass
    elif useUniversalStage:
        totalInitialMass = payloadMass + sum(stage["total_stage_mass"] for stage in stageSummaries)
    else:
        totalInitialMass = stageSummaries[0]["payload_mass"] + stageSummaries[0]["total_stage_mass"]
    computedStartMass = totalInitialMass if startMass is None else startMass
    auxiliaryMassBudget = computedStartMass - totalPropellantMass - payloadMass - existingAuxiliaryMass - customAuxiliaryMass
    return {
        "stage_count": len(stages),
        "stages": stageSummaries,
        "total_initial_mass": totalInitialMass,
        "total_construction_mass": sum(stage["construction_mass"] for stage in stageSummaries),
        "total_propellant_mass": totalPropellantMass,
        "payload_mass": payloadMass,
        "start_mass": computedStartMass,
        "existing_auxiliary_mass": existingAuxiliaryMass,
        "custom_auxiliary_systems": customAuxiliarySystems,
        "custom_auxiliary_mass": customAuxiliaryMass,
        "remaining_auxiliary_mass": auxiliaryMassBudget,
        "booster_diameter": boosterDiameter,
    }
        

class RCSThruster:
    """A class representing an RCS thruster. It contains information about the thrust, specific impulse, and propellant type."""
    def __init__(self, thrust, specificImpulse, propellantType, thrusterType, thrusterMass, propellantMass, thrustersQuantity=2):
        self.thrust = thrust
        self.specificImpulse = specificImpulse
        self.propellantType = propellantType
        self.thrusterType = thrusterType
        self.thrusterMass = thrusterMass*thrustersQuantity
        self.propellantMass = propellantMass
        self.propellantTankMaterial = 'AMg6'
        self.tankMaterialDensity = {
            'AMg6': 1800, # kg/m^3
            'Aluminum': 2700, # kg/m^3
            'Titanium': 4500, # kg/m^3
            'CarbonFiber': 1600, # kg/m^3
        }
        self.propellantTankDensity = self.tankMaterialDensity.get(self.propellantTankMaterial, 0)
        self.propellantTankType = 'Spherical'
        self.propellantTankThickness = 0.01
        if self.thrusterType == "Monopropellant":
            self.propellantTankMass = calculateRequiredTankVolume(self.propellantMass, self.propellantType, self.propellantType, gasCashionRatio=0) * self.tankMaterialDensity.get(self.propellantTankMaterial, 0) * self.propellantTankThickness
        elif self.thrusterType == "Bipropellant":
            self.propellantTankMass = calculateRequiredTankVolume(self.propellantMass, self.propellantType, self.propellantType, gasCashionRatio=0) * self.tankMaterialDensity.get(self.propellantTankMaterial, 0) * self.propellantTankThickness * 2 # Placeholder calculation for bipropellant tank mass, as it will depend on the specific design and requirements of the system.
        else:
            self.propellantTankMass = 0 # Placeholder value for propellant tank mass calculation, if an invalid thruster type is provided.


E11D458M = RCSThruster(thrust=392, specificImpulse=302/9.81, propellantType="MMH", thrusterType="Bipropellant", thrusterMass=3, propellantMass=50)


class launchVehicle:
    """A class representing a launch vehicle. It contains information about the stages of the vehicle and the total mass."""
    def __init__(self, payloadMass, maxPayloadDiameter, maxPayLoadLength, rocketName):
        self.payloadMass = payloadMass
        self.maxPayloadDiameter = maxPayloadDiameter
        self.maxPayLoadLength = maxPayLoadLength
        self.rocketName = rocketName
        
        
