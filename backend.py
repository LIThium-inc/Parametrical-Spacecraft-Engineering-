import math as m


MU = 4 * (10**14)
EARTH_RADIUS_M = 6_371_000
EARTH_RADIUS_KM = EARTH_RADIUS_M / 1000


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

