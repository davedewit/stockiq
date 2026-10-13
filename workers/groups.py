"""The share-screener worker groups: the one list every tool reads (workers/deploy.py, workers/prove.py, workers/build.py,
check-tools/workers.py). A new screener's workers: one line in GROUPS, and a line in MARKETS if its market is new."""

# group (the functions are <group>-1 ... <group>-N): (screener, number of functions, market)
GROUPS = {
    'stockiq-option-3-8-worker': ('Dow 30', 3, 'us'),
    'stockiq-option-3-7-worker': ('NASDAQ 100', 10, 'us'),
    'stockiq-option-3-1-worker': ('S&P 100', 10, 'us'),
    'stockiq-option-3-2-worker': ('S&P 400+600', 100, 'us'),
    'stockiq-option-3-4-worker': ('S&P 1500', 150, 'us'),
    'stockiq-option-3-5-worker': ('Russell 1000 (its first 50: S&P 500)', 100, 'us'),
    'stockiq-option-3-6-worker': ('Russell 2000', 200, 'us'),
    'stockiq-asia-5-1-worker': ('ASX 50', 5, 'asx'),
    'stockiq-asia-5-2-worker': ('ASX 100', 10, 'asx'),
    'stockiq-asia-5-3-worker': ('ASX 200', 20, 'asx'),
    'stockiq-asia-5-4-worker': ('ASX 300', 30, 'asx'),
    'stockiq-asia-5-5-worker': ('Nikkei 225', 21, 'tokyo'),
    'stockiq-europe-4-1-worker': ('FTSE 100', 10, 'london'),
    'stockiq-europe-4-2-worker': ('Germany DAX 40', 4, 'xetra'),
    'stockiq-europe-4-3-worker': ('France CAC 40', 4, 'paris'),
    'stockiq-europe-4-4-worker': ('Netherlands AEX', 3, 'amsterdam'),
    'stockiq-americas-6-1-worker': ('Canada TSX 60', 6, 'toronto'),
}

# market: the currency Yahoo quotes it in (London is pence), three symbols a freshly deployed worker is tried with, and the
# shares prove.py downloads two years of prices for (US shares mostly come from check-tools/paper-test/data/prices.json)
MARKETS = {
    'us': dict(currency='USD', try_with=['AAPL', 'MSFT', 'JPM'], sample='CRWD ZS DDOG MSTR TEAM LULU MELI PDD ASML ARM CSX KHC'.split()),
    'asx': dict(currency='AUD', try_with=['BHP.AX', 'CBA.AX', 'CSL.AX'], sample='BHP.AX CBA.AX CSL.AX NAB.AX WBC.AX ANZ.AX WES.AX MQG.AX WOW.AX TLS.AX RIO.AX FMG.AX'.split()),
    'tokyo': dict(currency='JPY', try_with=['7203.T', '6758.T', '9984.T'], sample='7203.T 6758.T 9984.T 8306.T 6861.T 9432.T 7974.T 6501.T 8035.T 4063.T 6098.T 9983.T'.split()),
    'london': dict(currency='GBp', try_with=['IMB.L', 'AZN.L', 'HSBA.L'], sample='IMB.L AZN.L HSBA.L SHEL.L ULVR.L BP.L GSK.L RIO.L LLOY.L BARC.L VOD.L BT-A.L'.split()),
    'xetra': dict(currency='EUR', try_with=['SAP.DE', 'SIE.DE', 'ALV.DE'], sample='SAP.DE SIE.DE ALV.DE DTE.DE AIR.DE MBG.DE BMW.DE BAS.DE MUV2.DE IFX.DE DBK.DE RWE.DE'.split()),
    'paris': dict(currency='EUR', try_with=['MC.PA', 'OR.PA', 'TTE.PA'], sample='MC.PA OR.PA TTE.PA SAN.PA AI.PA SU.PA BNP.PA CS.PA DG.PA SAF.PA EL.PA KER.PA'.split()),
    'amsterdam': dict(currency='EUR', try_with=['ASML.AS', 'INGA.AS', 'HEIA.AS'], sample='ASML.AS INGA.AS HEIA.AS AD.AS PHIA.AS UNA.AS WKL.AS PRX.AS ADYEN.AS KPN.AS AKZA.AS NN.AS'.split()),
    'toronto': dict(currency='CAD', try_with=['RY.TO', 'TD.TO', 'ENB.TO'], sample='RY.TO TD.TO ENB.TO CNR.TO SHOP.TO BNS.TO BMO.TO CP.TO SU.TO TRP.TO MFC.TO BCE.TO'.split()),
}

# The groups the page calls with a worker number and no stocks (group: the coordinator's key for its list). Their lists are
# in lists.txt, inside the package; build.py checks them against the coordinator's.
NUMBER_ONLY = {'stockiq-option-3-5-worker': '3-5', 'stockiq-option-3-6-worker': '3-6'}
