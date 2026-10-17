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
    'stockiq-europe-4-5-worker': ('Italy FTSE MIB', 4, 'milan'),
    'stockiq-europe-4-6-worker': ('Spain IBEX 35', 4, 'madrid'),
    'stockiq-asia-5-8-worker': ('Hong Kong Hang Seng', 10, 'hongkong'),
    'stockiq-asia-5-9-worker': ('Singapore STI', 3, 'singapore'),
    'stockiq-europe-4-7-worker': ('Switzerland SMI', 2, 'zurich'),
    'stockiq-asia-5-6-worker': ('India Sensex', 3, 'mumbai'),
    'stockiq-asia-5-7-worker': ('South Korea KOSPI 200', 21, 'seoul'),
    'stockiq-americas-6-2-worker': ('Brazil Bovespa', 8, 'saopaulo'),
    'stockiq-europe-4-8-worker': ('Euro Stoxx 50', 5, 'eurozone'),
    'stockiq-europe-4-9-worker': ('Sweden OMX Stockholm 30', 3, 'stockholm'),
    'stockiq-asia-5-10-worker': ('China CSI 300', 30, 'china'),
    'stockiq-asia-5-11-worker': ('Taiwan 50', 5, 'taipei'),
    'stockiq-asia-5-12-worker': ('New Zealand NZX 50', 5, 'wellington'),
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
    'milan': dict(currency='EUR', try_with=['ENEL.MI', 'ISP.MI', 'ENI.MI'], sample='ENEL.MI ISP.MI ENI.MI UCG.MI RACE.MI G.MI STLAM.MI PRY.MI LDO.MI TRN.MI SRG.MI MONC.MI'.split()),
    'madrid': dict(currency='EUR', try_with=['ITX.MC', 'SAN.MC', 'IBE.MC'], sample='ITX.MC SAN.MC IBE.MC BBVA.MC CABK.MC TEF.MC REP.MC AENA.MC FER.MC AMS.MC ELE.MC ACS.MC'.split()),
    'hongkong': dict(currency='HKD', try_with=['0005.HK', '0700.HK', '9988.HK'], sample='0005.HK 0700.HK 9988.HK 1299.HK 0939.HK 0941.HK 3690.HK 1810.HK 0388.HK 2318.HK 0883.HK 0016.HK'.split()),
    'singapore': dict(currency='SGD', try_with=['D05.SI', 'O39.SI', 'Z74.SI'], sample='D05.SI O39.SI U11.SI Z74.SI C6L.SI S68.SI BN4.SI C38U.SI A17U.SI F34.SI S63.SI G13.SI'.split()),
    'zurich': dict(currency='CHF', try_with=['NESN.SW', 'NOVN.SW', 'UBSG.SW'], sample='NESN.SW NOVN.SW RO.SW UBSG.SW ABBN.SW ZURN.SW CFR.SW SREN.SW HOLN.SW LONN.SW SIKA.SW GIVN.SW'.split()),
    'eurozone': dict(currency='EUR', try_with=['ASML.AS', 'SAP.DE', 'MC.PA'], sample='ASML.AS SAP.DE MC.PA SIE.DE TTE.PA ALV.DE SAN.MC IBE.MC ENEL.MI UCG.MI ABI.BR NDA-FI.HE'.split()),
    'stockholm': dict(currency='SEK', try_with=['ATCO-A.ST', 'INVE-B.ST', 'VOLV-B.ST'], sample='ATCO-A.ST INVE-B.ST VOLV-B.ST ABB.ST AZN.ST ERIC-B.ST HM-B.ST SEB-A.ST SAND.ST HEXA-B.ST ASSA-B.ST EQT.ST'.split()),
    'china': dict(currency='CNY', try_with=['600519.SS', '300750.SZ', '601318.SS'], sample='600519.SS 300750.SZ 601318.SS 600036.SS 000858.SZ 601166.SS 000333.SZ 600900.SS 601899.SS 002594.SZ 600030.SS 000001.SZ'.split()),
    'taipei': dict(currency='TWD', try_with=['2330.TW', '2317.TW', '2454.TW'], sample='2330.TW 2317.TW 2454.TW 2308.TW 2382.TW 2881.TW 2882.TW 2891.TW 3711.TW 2303.TW 2412.TW 1216.TW'.split()),
    'wellington': dict(currency='NZD', try_with=['FPH.NZ', 'AIA.NZ', 'IFT.NZ'], sample='FPH.NZ AIA.NZ IFT.NZ MEL.NZ CEN.NZ SPK.NZ ATM.NZ EBO.NZ MFT.NZ FBU.NZ AIR.NZ CNU.NZ'.split()),
    'mumbai': dict(currency='INR', try_with=['RELIANCE.NS', 'TCS.NS', 'M&M.NS'], sample='RELIANCE.NS TCS.NS HDFCBANK.NS INFY.NS ICICIBANK.NS ITC.NS LT.NS SBIN.NS BHARTIARTL.NS M&M.NS MARUTI.NS TITAN.NS'.split()),
    'seoul': dict(currency='KRW', try_with=['005930.KS', '000660.KS', '005380.KS'], sample='005930.KS 000660.KS 005380.KS 035420.KS 051910.KS 068270.KS 105560.KS 000270.KS 012330.KS 055550.KS 066570.KS 035720.KS'.split()),
    'saopaulo': dict(currency='BRL', try_with=['PETR4.SA', 'VALE3.SA', 'ITUB4.SA'], sample='PETR4.SA VALE3.SA ITUB4.SA BBDC4.SA ABEV3.SA BBAS3.SA WEGE3.SA B3SA3.SA RENT3.SA SUZB3.SA EMBJ3.SA GGBR4.SA'.split()),
}

# The groups the page calls with a worker number and no stocks (group: the coordinator's key for its list). Their lists are
# in lists.txt, inside the package; build.py checks them against the coordinator's.
NUMBER_ONLY = {'stockiq-option-3-5-worker': '3-5', 'stockiq-option-3-6-worker': '3-6'}
