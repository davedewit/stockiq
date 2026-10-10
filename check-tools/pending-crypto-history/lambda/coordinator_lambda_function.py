import json
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from textwrap import dedent

# Display wording for model output codes. StockIQ gives general information, not advice,
# so codes such as BUY / SELL are used internally but never shown.
_SIGNAL_LABELS = {
    'STRONG BUY': 'Strongly positive', 'BUY': 'Positive', 'MODERATE BUY': 'Slightly positive', 'CONSIDER': 'Slightly positive',
    'HOLD': 'Mixed', 'NEUTRAL': 'Mixed',
    'MODERATE SELL': 'Slightly negative', 'AVOID': 'Slightly negative', 'SELL': 'Negative', 'STRONG SELL': 'Strongly negative',
}
_HORIZON_LABELS = {
    'IMMEDIATE': 'Very short term', 'SHORT_TERM': 'Short term', 'SHORT-TERM': 'Short term', 'MEDIUM_TERM': 'Medium term',
    'MEDIUM-TERM': 'Medium term', 'LONG_TERM': 'Long term', 'LONG-TERM': 'Long term', 'DAY TRADE': 'Intraday', 'HOLD': 'n/a', 'AVOID': 'n/a',
}

def signal_label(code):
    # stock workers use underscores (STRONG_BUY, MODERATE_BUY ...), crypto workers use spaces;
    # an unknown code is shown as "Unrated" rather than guessed
    return _SIGNAL_LABELS.get(str(code or 'HOLD').replace('_', ' ').strip().upper(), 'Unrated')

def horizon_label(code):
    raw = str(code or '').strip()
    if not raw or raw == 'N/A':
        return 'n/a'
    return _HORIZON_LABELS.get(raw.upper(), raw)

# Worker URL mappings for each screener type
WORKER_URLS = {
    '3-100': [  # S&P 100 - 10 workers
        'https://tlpr2rgptntfwqvkcvwanx2giq0pttcu.lambda-url.us-east-1.on.aws/',
        'https://wr5phqprzpgdyc3e7jcxxndq440pxwdf.lambda-url.us-east-1.on.aws/',
        'https://hbbglzpw54g23zptuvjtpts7ji0akrzr.lambda-url.us-east-1.on.aws/',
        'https://ncr2kjqw5cgitmungtfhsjkpwu0lilnp.lambda-url.us-east-1.on.aws/',
        'https://mp43hke65xzp25zsgh7erv6ife0yiqds.lambda-url.us-east-1.on.aws/',
        'https://6orjqd6qpypkwnuu4oi6aghdv40belov.lambda-url.us-east-1.on.aws/',
        'https://3pvvrvhqy37bxx5yqplg33zk7i0vslsv.lambda-url.us-east-1.on.aws/',
        'https://2sggq4bqgcpu7tqhdlliorfpli0jdnae.lambda-url.us-east-1.on.aws/',
        'https://3pihnd5pesa4kudjzypvy2wcyi0hhjcp.lambda-url.us-east-1.on.aws/',
        'https://o3mxcz7qnfklw4mmazxjqlplke0balsi.lambda-url.us-east-1.on.aws/'
    ],
    '3-3': [  # S&P 500 - 50 workers (first 50 from Russell 1000)
        'https://sumuq55x4kzehluvsbjllokgt40sqziy.lambda-url.us-east-1.on.aws/',
        'https://4kxcesof3axkxjwxr7ppvxaufy0wxerx.lambda-url.us-east-1.on.aws/',
        'https://qdtaabefjq2uaxt7eolajnrpkq0cyjhp.lambda-url.us-east-1.on.aws/',
        'https://rnkpysopxjipqtwavfjox5gqji0fgkke.lambda-url.us-east-1.on.aws/',
        'https://okmwdoc56yby4ictlmccqlbji40jgrvt.lambda-url.us-east-1.on.aws/',
        'https://wtasa3lx3ui4o7p45ialc4jdwy0gubly.lambda-url.us-east-1.on.aws/',
        'https://tpsdzbraynuj2xugqwueofxxlq0dswgm.lambda-url.us-east-1.on.aws/',
        'https://mld3e7rdgljjoearp37f2rh4gq0jtdjd.lambda-url.us-east-1.on.aws/',
        'https://tv3puew6c5hn35lvdx4tiyhsbu0lalgg.lambda-url.us-east-1.on.aws/',
        'https://7yadzqcqosh6yptpoq4mw33uji0zzhaw.lambda-url.us-east-1.on.aws/',
        'https://ng5nhwpsdvaw32oljuoqwmyupe0gpuns.lambda-url.us-east-1.on.aws/',
        'https://fryd75bfv3vhpl4y7wk5axwkla0gdbmq.lambda-url.us-east-1.on.aws/',
        'https://y4udgwckvq5g4cyp4wuel72qn40bxaqn.lambda-url.us-east-1.on.aws/',
        'https://vun2rgrkvulfkp6bgpfgwre36m0majwy.lambda-url.us-east-1.on.aws/',
        'https://knwl34plyohgwqv654qaghtdiy0xxtfl.lambda-url.us-east-1.on.aws/',
        'https://j57tzdb336qy4rvn5ccqkjgxfy0whzkg.lambda-url.us-east-1.on.aws/',
        'https://lcydaogtuez3fakjbhzpvfqtuy0loywk.lambda-url.us-east-1.on.aws/',
        'https://2sep5fjrlbtyclb45hglcmxhay0uacnj.lambda-url.us-east-1.on.aws/',
        'https://brbz4bzc32kpiwy4fq3cvu4bzq0tvtob.lambda-url.us-east-1.on.aws/',
        'https://pilagfzilbgluzuvm35onlibm40makmv.lambda-url.us-east-1.on.aws/',
        'https://wisfookpyzku2ydy2dg2hk6hva0wfkag.lambda-url.us-east-1.on.aws/',
        'https://bkdbv3s2ld7saduhbi4yvzhrki0vgout.lambda-url.us-east-1.on.aws/',
        'https://6y6nufkvvp23chbr52fhmb5xoi0bgoej.lambda-url.us-east-1.on.aws/',
        'https://rkekhafr4cfw2vipdvnaktscqi0qxnze.lambda-url.us-east-1.on.aws/',
        'https://cqtjlp3eq6ndkor4tpdgos234m0qjwqo.lambda-url.us-east-1.on.aws/',
        'https://np2ybzlvwdtlozeyiz6k7eybdu0dcutk.lambda-url.us-east-1.on.aws/',
        'https://swoztkmizkdrgo6kwqnubx7zqy0axqne.lambda-url.us-east-1.on.aws/',
        'https://bruu4ufxhynlqtnbhczv3mdxpq0ckkvm.lambda-url.us-east-1.on.aws/',
        'https://wxgjriaxwe3zwpx7qwfyfbbizi0srlvr.lambda-url.us-east-1.on.aws/',
        'https://2fyrvclcxmg5xjaga35pr76vhm0lyqws.lambda-url.us-east-1.on.aws/',
        'https://b4ymcbihbumuu4vjcj3skunug40zhjtd.lambda-url.us-east-1.on.aws/',
        'https://izqjvti6fv4nudhyopaeiksku40drdtu.lambda-url.us-east-1.on.aws/',
        'https://bhguocquvafpnheauoup7ylzba0kbfov.lambda-url.us-east-1.on.aws/',
        'https://cyc67g4bqes5fgcnglkevk4ytm0ntesv.lambda-url.us-east-1.on.aws/',
        'https://edyuklsnhlosrxr6fmotkfkoi40yzdut.lambda-url.us-east-1.on.aws/',
        'https://uylcsrvc2jrfvavusaww3d2iui0haprp.lambda-url.us-east-1.on.aws/',
        'https://eia6ugy35abq74qkzh4tea5mfy0uzqlg.lambda-url.us-east-1.on.aws/',
        'https://6jpb4qa76l3t6tg4atl42wjqdi0sahyo.lambda-url.us-east-1.on.aws/',
        'https://bscu2mkvp7sabovzpa66g7jhiu0waakd.lambda-url.us-east-1.on.aws/',
        'https://auyg6ifl2okkforyps6akdl2nu0cdtpx.lambda-url.us-east-1.on.aws/',
        'https://krfqvkj2xot3yweyhcbarrwwfy0pdiap.lambda-url.us-east-1.on.aws/',
        'https://edfmppbagwitqpcelejfyqoski0yanmx.lambda-url.us-east-1.on.aws/',
        'https://mc6mev6tq56fqfvmdkkhxidb6e0ujymq.lambda-url.us-east-1.on.aws/',
        'https://gpardfscnzctwj2lau5cltp3nm0grpro.lambda-url.us-east-1.on.aws/',
        'https://bej54is7mwvzh33rc7nc2cloim0yhztv.lambda-url.us-east-1.on.aws/',
        'https://ar6uiuqa6itnfh7zk4eu6j2klq0yqblj.lambda-url.us-east-1.on.aws/',
        'https://lsqk6sqqdhychyajeeqrnj2tiu0ydnde.lambda-url.us-east-1.on.aws/',
        'https://xogt75owsex4uksgrltxgfr4sq0dyhss.lambda-url.us-east-1.on.aws/',
        'https://tftb664a3u34ilzny2hjrdp4jm0gpkcr.lambda-url.us-east-1.on.aws/',
        'https://ujx3d42fokwn3m2gno3sknrhp40itbij.lambda-url.us-east-1.on.aws/'
    ],
    '3-7': [  # NASDAQ 100 - 10 workers
        'https://522jr4z2s7sxppxjpxsxs3wbaq0ifsve.lambda-url.us-east-1.on.aws/',
        'https://argv7wfeqoxd63pjvlk2btgu6y0ikqkl.lambda-url.us-east-1.on.aws/',
        'https://achfptgbrn5t2godpzbc2ukbve0fufie.lambda-url.us-east-1.on.aws/',
        'https://evc43jaybk4ibkkkbbjslrmfrm0qccbo.lambda-url.us-east-1.on.aws/',
        'https://4bnwvfcnbbeoh6yckzu5gdfcse0wgnkl.lambda-url.us-east-1.on.aws/',
        'https://6jz4q6ubw6ggwrlfksid7b6z2q0lkbjw.lambda-url.us-east-1.on.aws/',
        'https://mzia3uzyzwqdgji57hpzillmpa0vlwmo.lambda-url.us-east-1.on.aws/',
        'https://u637oomkd52o57kxz5izekfnpi0dpbiq.lambda-url.us-east-1.on.aws/',
        'https://saecx4cms7zq655v47pheflzga0fator.lambda-url.us-east-1.on.aws/',
        'https://nht4utoktc2apuxaokqqmvauvi0vassn.lambda-url.us-east-1.on.aws/'
    ],
    '3-2': [  # S&P 400+600 - 100 workers
        'https://z2uvmjn3atygvi3q4lzeavjn2u0kafxs.lambda-url.us-east-1.on.aws/',
        'https://rvhpejzgjfnhnsrgkf67d4cdem0tuprx.lambda-url.us-east-1.on.aws/',
        'https://nvt3fsj6w7jqt3w7eta6cdvd3a0jgunp.lambda-url.us-east-1.on.aws/',
        'https://pmnvy5np7rxsa6iy4kablleysm0zebkn.lambda-url.us-east-1.on.aws/',
        'https://z6v74ptw3ygwyzgz3mdbwvndyq0zwzpz.lambda-url.us-east-1.on.aws/',
        'https://oakylw54tibnnyuebcg2v6htfm0urgob.lambda-url.us-east-1.on.aws/',
        'https://jdsb672fhg52t6cog4ayya7mwq0vsygm.lambda-url.us-east-1.on.aws/',
        'https://ftou3qvsl74sjjwyybhghzieum0yrojo.lambda-url.us-east-1.on.aws/',
        'https://26xvk6gleal2i7r4zukr6eeiqy0kksqj.lambda-url.us-east-1.on.aws/',
        'https://3wc2xgg2xmuizs7anh3kchngyu0ljtkt.lambda-url.us-east-1.on.aws/',
        'https://cnzqyg6ql2mtgagdrrweji3wc40ftqkx.lambda-url.us-east-1.on.aws/',
        'https://2efokdsjzbkp66n27lvmpqjslq0zfoei.lambda-url.us-east-1.on.aws/',
        'https://2sneyqqfilfygin5dqr5hlduhu0zmakl.lambda-url.us-east-1.on.aws/',
        'https://4ki6pxopyheronpvij7glyqb4y0hkeuc.lambda-url.us-east-1.on.aws/',
        'https://kfls7jxvqusucgy6i7ysblrebi0dnagf.lambda-url.us-east-1.on.aws/',
        'https://iucm2ec36y27hvk2kib4ailc2e0fmkls.lambda-url.us-east-1.on.aws/',
        'https://uo3xljx6iux6qtc6wiwvazqgzi0pgnnh.lambda-url.us-east-1.on.aws/',
        'https://uypvmog6bmmtbgkzrq6phwjnzm0fjjzg.lambda-url.us-east-1.on.aws/',
        'https://ftzduqjsfyfs4mfvpfveubqzom0joaty.lambda-url.us-east-1.on.aws/',
        'https://worhw5uqotvwrjgirzcpn7gepi0jruke.lambda-url.us-east-1.on.aws/',
        'https://ziwm7xzillgzdhdaax7w6nys6e0eveah.lambda-url.us-east-1.on.aws/',
        'https://m63ulgrrhv6q7dajq2jbov4plm0blswb.lambda-url.us-east-1.on.aws/',
        'https://g6xc4gbczm5yog7re4vtptugpe0yxkyk.lambda-url.us-east-1.on.aws/',
        'https://wvjpnlcvpn4bqbwpk7u3iemxw40einnm.lambda-url.us-east-1.on.aws/',
        'https://ujrpvzvq3jnkh6gbtaov44ps6i0llcuv.lambda-url.us-east-1.on.aws/',
        'https://vdna3gpoe35begeqyezlxlbi4a0qlboo.lambda-url.us-east-1.on.aws/',
        'https://herh3dn5zwe2kplf2fl2b7hq2e0kwnvu.lambda-url.us-east-1.on.aws/',
        'https://m7hqpxn2u2luautwlhddalb6om0nshmh.lambda-url.us-east-1.on.aws/',
        'https://6gw6mu4ypt62j2ml3b6bltmfmu0liwqv.lambda-url.us-east-1.on.aws/',
        'https://2yz3poakqilfjrfdwokxjefazq0lbmls.lambda-url.us-east-1.on.aws/',
        'https://pxrgmwg26zkfxv5554t2s7psii0gwwat.lambda-url.us-east-1.on.aws/',
        'https://yxe5dkp7fombm25y3yb6zfbzvi0xpnsr.lambda-url.us-east-1.on.aws/',
        'https://tifouiewoeqhq2nnzjnkclosqy0zktxt.lambda-url.us-east-1.on.aws/',
        'https://z5klxtguvzsvjmj3xvfrhunixm0vcriy.lambda-url.us-east-1.on.aws/',
        'https://oyrqj3d4m6v5lm2rg4jvwlpbra0ebvnz.lambda-url.us-east-1.on.aws/',
        'https://vw46xed7fpf67mpu6bkdddimjm0cziqr.lambda-url.us-east-1.on.aws/',
        'https://iz52u7tjwqfy4froxnrkg3fymu0qjevh.lambda-url.us-east-1.on.aws/',
        'https://mhp2aqwzvga67ct5dcbpf3xnoi0wdkpw.lambda-url.us-east-1.on.aws/',
        'https://fvmdtquzd2rh6vdyqyyqcieuma0wpogn.lambda-url.us-east-1.on.aws/',
        'https://epkgxvwfsxx57jomyx72rmb7hq0nihcb.lambda-url.us-east-1.on.aws/',
        'https://wdxzr6tmuttghwe3ihcgxmej6i0reevm.lambda-url.us-east-1.on.aws/',
        'https://egtkwpmxjt7kkxo2n6esanv5wa0dzied.lambda-url.us-east-1.on.aws/',
        'https://2og55wlbpnfhsm2rkdq6mh4ohy0peyrx.lambda-url.us-east-1.on.aws/',
        'https://56s6nviw54mepjohwdsw742ppi0fbpvt.lambda-url.us-east-1.on.aws/',
        'https://i5yh2sehcdmcfsvthpjvwgzgju0jzgbd.lambda-url.us-east-1.on.aws/',
        'https://nbgx7cizykt2d2ftqwukxszqou0jfuws.lambda-url.us-east-1.on.aws/',
        'https://zdkdahxzcj4abphuut4rs7uacy0mrqht.lambda-url.us-east-1.on.aws/',
        'https://pms4hqcfw7bk5izqqrzy5y2qda0jocly.lambda-url.us-east-1.on.aws/',
        'https://gnd54yetmjqbu3guxvijegvhs40fzhvo.lambda-url.us-east-1.on.aws/',
        'https://ujnqnanks545spk6cw3gqxha4i0okmgm.lambda-url.us-east-1.on.aws/',
        'https://vjhwvp4eh64iyoyamfj2yovtba0ingfq.lambda-url.us-east-1.on.aws/',
        'https://bx3qcuedcotz23dnqd2se6ktx40khfze.lambda-url.us-east-1.on.aws/',
        'https://c6walrka5arxutj4jp47qq67ma0cngpm.lambda-url.us-east-1.on.aws/',
        'https://wadzrxsetgpzuevtqqbqfz3zju0ekavy.lambda-url.us-east-1.on.aws/',
        'https://ncmfcqdsqgtw5idnbyrc45wm4u0phffu.lambda-url.us-east-1.on.aws/',
        'https://ztsjyvkfmkrh4ifydxzt3fnw240gjphy.lambda-url.us-east-1.on.aws/',
        'https://bkadcvyhjexv663oznj5idy2we0dfelq.lambda-url.us-east-1.on.aws/',
        'https://nc7ogpmmeturbtm6mhvgznf4hu0gdogs.lambda-url.us-east-1.on.aws/',
        'https://f2jo46hudri7jnkloc74iwbosm0oskit.lambda-url.us-east-1.on.aws/',
        'https://6oqqp5q4phq7clz4vuorhlycye0nilnc.lambda-url.us-east-1.on.aws/',
        'https://v5tgvksgvdffbl65zysh2bcwti0fsash.lambda-url.us-east-1.on.aws/',
        'https://5wk34ksv34kjfd3233uapjwynq0frblg.lambda-url.us-east-1.on.aws/',
        'https://6minzcwo3pddzfeqppfenqpeqi0knjfz.lambda-url.us-east-1.on.aws/',
        'https://wkqbxddtmlbm4whnntlu3fxfum0oovpe.lambda-url.us-east-1.on.aws/',
        'https://uvf2bpw4kd644m5i2nt7qmsqim0fgwva.lambda-url.us-east-1.on.aws/',
        'https://5f3yqmxoqqygrwu4rsm5uwy4h40wcgnf.lambda-url.us-east-1.on.aws/',
        'https://syz6aayztrekwqofkva3pktfwi0ulxfl.lambda-url.us-east-1.on.aws/',
        'https://cnhve7wumhht6tbkexcefdr6be0fbfef.lambda-url.us-east-1.on.aws/',
        'https://hf7vbvombskuosan4afqbxx5fy0nbazn.lambda-url.us-east-1.on.aws/',
        'https://xvx2xwztst4cwj52mrnobsdhgm0ndiwp.lambda-url.us-east-1.on.aws/',
        'https://wrfvhixucxseeun2tezodr32qq0kstqn.lambda-url.us-east-1.on.aws/',
        'https://a67h5mgmx3ihdkrzfmyhutaany0oiynf.lambda-url.us-east-1.on.aws/',
        'https://gaxarhm3e7mrv6xuohtakjbppy0tvfxw.lambda-url.us-east-1.on.aws/',
        'https://yognynooiegu4o6k3cdjktcmre0dgpqs.lambda-url.us-east-1.on.aws/',
        'https://mdh4xti5v7ftfhfnco4hv7cb3i0ejskk.lambda-url.us-east-1.on.aws/',
        'https://4vnl7yi7cmaofh6x2swdg3w2540gdbgc.lambda-url.us-east-1.on.aws/',
        'https://iddjdhf2lq6az6hp5wmf2bnu3m0okwyi.lambda-url.us-east-1.on.aws/',
        'https://2pf6qkvwxiluxa6zzix53fsv340tvszp.lambda-url.us-east-1.on.aws/',
        'https://m6logq2mmvjasu5bqj2xgpqvj40arssw.lambda-url.us-east-1.on.aws/',
        'https://iinjspd3qb5yuo5ccsdiadlzve0fsmbs.lambda-url.us-east-1.on.aws/',
        'https://rmvnn447kwypu4shnyxmt2e7ze0oglks.lambda-url.us-east-1.on.aws/',
        'https://tnyas6svmb2xi7wn64szpyvkj40svnxs.lambda-url.us-east-1.on.aws/',
        'https://gznqas23tjdav6tmzpcpgu3mr40kfgck.lambda-url.us-east-1.on.aws/',
        'https://fopmu3zule5uvuuuurd7lzpcjy0wsutj.lambda-url.us-east-1.on.aws/',
        'https://bg5pyya6jy7l733dobfjfpcrvy0acicp.lambda-url.us-east-1.on.aws/',
        'https://kp4hbtl7odq2lw4w622yyvkvhq0vykkt.lambda-url.us-east-1.on.aws/',
        'https://gjr3tn3wjdm74jwvlaizoorh440oceia.lambda-url.us-east-1.on.aws/',
        'https://kctcghznhd73w3iucictz74nby0geqxa.lambda-url.us-east-1.on.aws/',
        'https://gmr7qwpxictsvtocsbfprrenkm0bookf.lambda-url.us-east-1.on.aws/',
        'https://xyyavzlmhf2th233aotk3ix3he0tzixr.lambda-url.us-east-1.on.aws/',
        'https://f5zp6nn6c2aouuvhvrlb3naezm0iacnp.lambda-url.us-east-1.on.aws/',
        'https://g4zhdv2ft4mebive3vlk5qch5a0ndfrx.lambda-url.us-east-1.on.aws/',
        'https://w5vzwdzpj7ytayhn5kzfnhjuz40ergyj.lambda-url.us-east-1.on.aws/',
        'https://jvymk4spd4franoyitxn2433vy0puqmw.lambda-url.us-east-1.on.aws/',
        'https://ufr7nkbsf7qdvsq6z25iuuruoy0qdmho.lambda-url.us-east-1.on.aws/',
        'https://qmqafl5d27wg4xsxnyr42gzive0gxose.lambda-url.us-east-1.on.aws/',
        'https://mvprfbxmbovchf65cswo3jithy0njpaa.lambda-url.us-east-1.on.aws/',
        'https://k4xpknbxq5otq6ihaed3biydgq0whfev.lambda-url.us-east-1.on.aws/',
        'https://byl2moeijrtft3ytxqjyzcdo4a0thzlg.lambda-url.us-east-1.on.aws/',
        'https://hb52ymfij5mqf52fledjv5yksq0nvoxf.lambda-url.us-east-1.on.aws/'
    ],
    '3-4': [],  # S&P 1500 - 150 workers (uses worker_id)
    '3-5': [],  # Russell 1000 - 100 workers (uses worker_id)
    '3-6': [],  # Russell 2000 - 200 workers (uses worker_id)
    '3-8': [  # Dow 30 - 3 workers
        'https://5tuk56sksvrka5m56epcchxciy0yhsvo.lambda-url.us-east-1.on.aws/',
        'https://et6use2hjiidm3xxt2xidrhx2m0rogyr.lambda-url.us-east-1.on.aws/',
        'https://uhrbaqx53y4fyfvy3xc2wcuvoe0csuby.lambda-url.us-east-1.on.aws/'
    ],
    '4-50': [  # ASX 50 - 5 workers (NEW asia-5-1)
        'https://ph2koddgkibjl3wujln3zlde6q0vahci.lambda-url.us-east-1.on.aws/',
        'https://mfsznkzz5segvhk67tbx4mk6w40zzlvg.lambda-url.us-east-1.on.aws/',
        'https://ivbqyey3lpsin3xn5w56sxklvq0ladtw.lambda-url.us-east-1.on.aws/',
        'https://226ww6ocvpgd446wct3xhsqsgu0wgowy.lambda-url.us-east-1.on.aws/',
        'https://cfkugbbpzftz2sydotebdfbp2u0wthxz.lambda-url.us-east-1.on.aws/'
    ],

    '4-100': [  # ASX 100 - 10 workers (NEW asia-5-2)
        'https://pt6gjtfjbmvd5gvzzgpr7exyq40jdgft.lambda-url.us-east-1.on.aws/',
        'https://y6w3gnwzwyylnrffntv4jltxga0ayscs.lambda-url.us-east-1.on.aws/',
        'https://u4rw4bf25qouie2r4x4t3te6ty0zkefj.lambda-url.us-east-1.on.aws/',
        'https://fpt5i57mdacde2c7i4d424crqe0pplxx.lambda-url.us-east-1.on.aws/',
        'https://v2dphlet5zpjgs4n2zdyszneaq0gnwgf.lambda-url.us-east-1.on.aws/',
        'https://jmjxar6kkiwxy2nlvkaawyniby0itfoh.lambda-url.us-east-1.on.aws/',
        'https://qdtxs3h2u42hloqisbluv25xqq0riyrn.lambda-url.us-east-1.on.aws/',
        'https://pwsecih7aybzcjweigzdqemkoq0yidng.lambda-url.us-east-1.on.aws/',
        'https://m7brwtlpgosupso2be5mtwjmgu0ztctq.lambda-url.us-east-1.on.aws/',
        'https://voabf7i5mfv4hxfskfxstmty5m0onvwc.lambda-url.us-east-1.on.aws/'
    ],
    '4-200': ["https://zdmbi2py4r4ve2c2qktlew4fhm0zewvz.lambda-url.us-east-1.on.aws/","https://eq5p62fptsiohcplc6rni6ynmu0flxbc.lambda-url.us-east-1.on.aws/","https://g5srxjsnywgv5dpq346fe5bjzy0pjrbc.lambda-url.us-east-1.on.aws/","https://dfbi7p5zyfdw2ts6eq7sykspwu0bhwee.lambda-url.us-east-1.on.aws/","https://oa2jwfnf3bdkfdtpkoqylkzglm0qcmug.lambda-url.us-east-1.on.aws/","https://ceruwdnkbl3rq6pdy3ttm4w4ty0jxnai.lambda-url.us-east-1.on.aws/","https://qj23e6w4szjz4mlxnr6vaxy3eq0tkoks.lambda-url.us-east-1.on.aws/","https://xkfzof47xqcfvagj7kmogve2e40juauq.lambda-url.us-east-1.on.aws/","https://z7im4wlhmnuehbpo5xsor6adr40pwsit.lambda-url.us-east-1.on.aws/","https://7zdpmqcgcxl6y55pcnjchgby5u0jhcim.lambda-url.us-east-1.on.aws/","https://4nsyylypuzscrnuwbmvhmshgc40hvdkf.lambda-url.us-east-1.on.aws/","https://wxbbxlikfmmhsxgwqhps4k2iuq0wuukb.lambda-url.us-east-1.on.aws/","https://tr5ak3x54hjpmekmwah3ipw4de0neqbz.lambda-url.us-east-1.on.aws/","https://a4l3kgi4efmoi6wzan7yx3fbti0ecffs.lambda-url.us-east-1.on.aws/","https://ljyzdni5qkl7nhwatcogo6h5am0xbjaj.lambda-url.us-east-1.on.aws/","https://bwdfqojou5k4fw56o546b7lkm40yfjpk.lambda-url.us-east-1.on.aws/","https://7y4suxzwnilygsuhpu4grsmq4u0mmjar.lambda-url.us-east-1.on.aws/","https://dix4r6zsygayuvp3gloeyfa7oy0pydit.lambda-url.us-east-1.on.aws/","https://z3fcgzcux4jnte2ywnnoe63qu40jkjuy.lambda-url.us-east-1.on.aws/","https://djcngojfo2e6rr5sq6unuwnwcu0ngbwy.lambda-url.us-east-1.on.aws/"],  # ASX 200 - 20 workers (NEW asia-5-3)
    '4-300': ["https://jfbmkyluzunuoamftazpkijegm0ljegs.lambda-url.us-east-1.on.aws/","https://kkb773jiw72ftsofcnfbrgftp40rhfjy.lambda-url.us-east-1.on.aws/","https://ionfnx6iewltqwmrvedfn3owie0afihf.lambda-url.us-east-1.on.aws/","https://7tfypws4nqb3iqr7olibawmbfm0jlzjs.lambda-url.us-east-1.on.aws/","https://ezp5mxhvwmy6qhy3r4acsuwm4m0dglyt.lambda-url.us-east-1.on.aws/","https://xremswiroprvjuto6vxndbybnm0xkrsy.lambda-url.us-east-1.on.aws/","https://rvkyl4td6a42d7dfjlyskdyisa0eptwf.lambda-url.us-east-1.on.aws/","https://pluquaig762ddynuskdtzhqgqm0sohcb.lambda-url.us-east-1.on.aws/","https://qz5piciswsf5pvpetmp4kq24wu0yuort.lambda-url.us-east-1.on.aws/","https://4mb2o5ond47etn3jsctl4nu42a0yapsj.lambda-url.us-east-1.on.aws/","https://3wxulmrsrkmahjst5nsi2eucqa0vssvl.lambda-url.us-east-1.on.aws/","https://b5lvrk5jaa5ap6lnsx62b34uai0bunpm.lambda-url.us-east-1.on.aws/","https://wkripfsvmcefrnc5ndfrrieecq0mdecc.lambda-url.us-east-1.on.aws/","https://r2pkfsogy4k6coqmhah7hydu3u0rgazz.lambda-url.us-east-1.on.aws/","https://gzz4mfxgjgbdah5umv3rnl2cuu0jxzlq.lambda-url.us-east-1.on.aws/","https://pyrcu4gmwasuhou3uypi44xxom0rwfad.lambda-url.us-east-1.on.aws/","https://s6x3eewnmt6ziqez5zengtgyvu0gjwgo.lambda-url.us-east-1.on.aws/","https://s6iixoj2z4iincdic7j2pzesny0cfgbp.lambda-url.us-east-1.on.aws/","https://jxq3qwsck6f3b3s2jejhfxqsf40kezta.lambda-url.us-east-1.on.aws/","https://wmmvyxqsn4ub4vymsgvbrbhvni0sqafe.lambda-url.us-east-1.on.aws/","https://7xfnmowroamq3pzxe2765iwa5y0npnwn.lambda-url.us-east-1.on.aws/","https://23gujxpbnniygjodznwrtcn6be0eqjfj.lambda-url.us-east-1.on.aws/","https://ldigoeb33fphdfcpfaqjgibbdu0htetb.lambda-url.us-east-1.on.aws/","https://gxasl2yhcvk3apym7azkonv6xy0ypwoh.lambda-url.us-east-1.on.aws/","https://xt3uhsu2jlb4w3j4hhgrup46oa0oeosu.lambda-url.us-east-1.on.aws/","https://cnnpxpsvwjmwu5ubkhjddptyoq0nxllx.lambda-url.us-east-1.on.aws/","https://fhltlxnqv3c74ykqnwhciqvdri0fduon.lambda-url.us-east-1.on.aws/","https://m6hbjbtnrzirqq3njul3ca57ru0wydar.lambda-url.us-east-1.on.aws/","https://mxyh4ed7lqdhokwkjap55vezcu0grnui.lambda-url.us-east-1.on.aws/","https://tzwthsohhoj2nifkjw5gcftyxq0hwhut.lambda-url.us-east-1.on.aws/"],  # ASX 300 - 30 workers (NEW asia-5-4)
    '5-ftse100': [  # UK FTSE 100 - 10 workers (NEW europe-4-1)
        'https://jj3bbmgmeqab6zeksees37cute0tncvs.lambda-url.us-east-1.on.aws/',
        'https://rxsr5ewpafmciqetbdjh4senta0kliqw.lambda-url.us-east-1.on.aws/',
        'https://cmrjcsekzumxpiic7curdzt3im0qeycx.lambda-url.us-east-1.on.aws/',
        'https://hkdsj5m5ylokvom7hxeqw34say0xigse.lambda-url.us-east-1.on.aws/',
        'https://7o7sh53vljvmerskx5xxj5sgwu0hunbt.lambda-url.us-east-1.on.aws/',
        'https://kptbydm2z6vnzxcehdono4wgmm0msidt.lambda-url.us-east-1.on.aws/',
        'https://f7erkcsokxbgux7grz2matjnme0ydaie.lambda-url.us-east-1.on.aws/',
        'https://4ovkozqbxggwdldbwlghptuwfm0mkibm.lambda-url.us-east-1.on.aws/',
        'https://rxobsfprrrlv2x2ta5eim7q5oa0azgpk.lambda-url.us-east-1.on.aws/',
        'https://pbfu2jxvnkle2zzzmm7czrdgum0xnhkm.lambda-url.us-east-1.on.aws/'
    ],
    '5-nikkei225': [  # Japan Nikkei 225 - 21 workers (asia-5-5)
        'https://2g3hj5stpbtprg63efqstjrboy0mwpog.lambda-url.us-east-1.on.aws/',   # worker-1
        'https://5yzugqqawscfvx5kyqict6x7ha0samau.lambda-url.us-east-1.on.aws/',   # worker-2
        'https://wfeof7dr5inqc4xhohtdu6n6bi0epuqg.lambda-url.us-east-1.on.aws/',   # worker-3
        'https://itrpfcyqqn6yzjqn6ky7dynnoe0ixzfk.lambda-url.us-east-1.on.aws/',  # worker-4
        'https://s6kwr3a6j7u4x2a6gbqnrjj6s40nunos.lambda-url.us-east-1.on.aws/',  # worker-5
        'https://t4uvfpm7ewvvdfn7xpu7hhj6ua0edjse.lambda-url.us-east-1.on.aws/',  # worker-6
        'https://76pscw2vi3chb2dxjqtuqrha740gvxwu.lambda-url.us-east-1.on.aws/',  # worker-7
        'https://4bjpk7ivpav7hoalmiphib4twm0vuwmr.lambda-url.us-east-1.on.aws/',  # worker-8
        'https://knvjsgs77qj6k7zlpe2jqo2vle0sdtju.lambda-url.us-east-1.on.aws/',  # worker-9
        'https://hx6hgfuntjvk5tmhqsrywvy5a40wtuyq.lambda-url.us-east-1.on.aws/',  # worker-10
        'https://uullmljyan3vuybanguja2h5py0jevfr.lambda-url.us-east-1.on.aws/',   # worker-11
        'https://td2j3copshrmq4vehgpujezsvy0mcwtm.lambda-url.us-east-1.on.aws/',  # worker-12
        'https://6utz7752pa3l54lujtsnq4gh240oepjs.lambda-url.us-east-1.on.aws/',  # worker-13
        'https://7fqznbw7547jehwmg5har3zh4q0pdzcq.lambda-url.us-east-1.on.aws/',  # worker-14
        'https://xxjl5khbatuobsoxwe4csx6bgy0tmkse.lambda-url.us-east-1.on.aws/',  # worker-15
        'https://ueqire27pt3nzwkgzlal5nnlau0mxnxr.lambda-url.us-east-1.on.aws/',  # worker-16
        'https://sla4c77w4je62je2p7igbsm76i0tgafz.lambda-url.us-east-1.on.aws/',  # worker-17
        'https://76vbcb5lp4yp5hgwy3xn72nbm40oofqx.lambda-url.us-east-1.on.aws/',  # worker-18
        'https://i5vrx42zdwq7yt777ii4nqqgem0ngayb.lambda-url.us-east-1.on.aws/',  # worker-19
        'https://g3vxxlz4p6s7dum3c6cwwguawe0jladz.lambda-url.us-east-1.on.aws/',  # worker-20
        'https://3dmddgt36bvz2hqsqj3mghd2540drkom.lambda-url.us-east-1.on.aws/'   # worker-21
    ],
    '7-1': ['https://5fyemil3eipbwqyyb2kloijyhi0uvtct.lambda-url.us-east-1.on.aws/']  # Crypto orchestrator
}

STOCK_UNIVERSES = {
    '3-100': ['AAPL','ABBV','ABT','ACN','ADBE','AMAT','AMD','AMGN','AMT','AMZN','ANET','AVGO','AXP','BA','BAC','BKNG','BLK','BMY','BNY','BRK-B','C','CAT','CMCSA','COF','COP','COST','CRM','CSCO','CVS','CVX','DE','DELL','DHR','DIS','DUK','EMR','FDX','GD','GE','GEV','GILD','GM','GOOG','GOOGL','GS','HD','IBM','INTC','INTU','ISRG','JNJ','JPM','KO','LIN','LLY','LMT','LOW','LRCX','MA','MCD','MDLZ','MDT','META','MMM','MO','MRK','MS','MSFT','MU','NEE','NFLX','NOW','NVDA','ORCL','PANW','PEP','PFE','PG','PLTR','PM','QCOM','RTX','SBUX','SCHW','SNDK','SO','T','TMO','TMUS','TSLA','TXN','UBER','UNH','UNP','UPS','USB','V','VZ','WFC','WMT','XOM'],
    '3-3': ['MMM','AOS','ABT','ABBV','ACN','ADBE','AMD','AES','AFL','A','APD','ABNB','AKAM','ALB','ARE','ALGN','ALLE','LNT','ALL','GOOGL','GOOG','MO','AMZN','AMCR','AEE','AEP','AXP','AIG','AMT','AWK','AMP','AME','AMGN','APH','ADI','AON','APA','APO','AAPL','AMAT','APP','APTV','ACGL','ADM','ARES','ANET','AJG','AIZ','T','ATO','ADSK','ADP','AZO','AVY','AXON','BKR','BALL','BAC','BAX','BDX','BRK-B','BBY','TECH','BIIB','BLK','BX','XYZ','BE','BNY','BA','BKNG','BSX','BMY','AVGO','BR','BRO','BF-B','BG','BXP','CHRW','CDNS','CPT','COF','CAH','CCL','CARR','CVNA','CASY','CAT','CBOE','CBRE','CDW','COR','CNC','CNP','CF','CRL','SCHW','CHTR','CVX','CMG','CB','CHD','CIEN','CI','CINF','CTAS','CSCO','C','CFG','CLX','CME','CMS','KO','CTSH','COHR','COIN','CL','CMCSA','FIX','COP','ED','STZ','CEG','COO','CPRT','GLW','CPAY','CSGP','COST','CRH','CRWD','CCI','CSX','CMI','CVS','DHR','DRI','DDOG','DVA','DECK','DE','DELL','DAL','DVN','DXCM','FANG','DLR','DG','DLTR','D','DPZ','DASH','DOV','DOW','DHI','DTE','DUK','DD','ETN','EBAY','ECHO','ECL','EIX','EW','ELV','EME','EMR','ETR','EOG','EQT','EFX','EQIX','ERIE','ESS','EL','EG','EVRG','P','ES','EXC','EXE','EXPE','EXPD','EXR','XOM','FFIV','FDS','FICO','FAST','FRT','FDX','FDXF','FERG','FIS','FITB','FSLR','FE','FISV','FLEX','F','FTNT','FTV','FOXA','FOX','BEN','FCX','GRMN','IT','GE','GEHC','GEV','GEN','GNRC','GD','GIS','GM','GPC','GILD','GPN','GL','GDDY','GS','HAL','HIG','HAS','HCA','DOC','HSIC','HSY','HPE','HLT','HD','HONA','HON','HRL','HST','HWM','HPQ','HUBB','HUM','HBAN','HII','IBM','IEX','IDXX','ITW','ILMN','INCY','IR','PODD','INTC','IBKR','ICE','IFF','IP','INTU','ISRG','IVZ','INVH','IQV','IRM','JBHT','JBL','JKHY','J','JNJ','JCI','JPM','KVUE','KDP','KEY','KEYS','KMB','KIM','KMI','KKR','KLAC','KHC','KR','LHX','LH','LRCX','LVS','LDOS','LEN','LII','LLY','LIN','LYV','LMT','L','LOW','LULU','LITE','LYB','MTB','MPC','MAR','MRSH','MLM','MRVL','MAS','MA','MKC','MCD','MCK','MDT','MRK','META','MET','MTD','MGM','MCHP','MU','MSFT','MAA','MRNA','MDLZ','MPWR','MNST','MCO','MS','MOS','MSI','MSCI','NDAQ','NTAP','NFLX','NEM','NWSA','NWS','NEE','NKE','NI','NDSN','NSC','NTRS','NOC','NCLH','NRG','NUE','NVDA','NVR','NXPI','ORLY','OXY','ODFL','OMC','ON','OKE','ORCL','OTIS','PCAR','PKG','PLTR','PANW','PH','PAYX','PYPL','PNR','PEP','PFE','PCG','PM','PSX','PNW','PNC','PPG','PPL','PFG','PG','PGR','PLD','PRU','PEG','PTC','PSA','PHM','PWR','QCOM','DGX','Q','RL','RJF','RDDT','RTX','O','REG','REGN','RF','RSG','RMD','RVTY','HOOD','ROK','ROL','ROP','ROST','RCL','SPGI','CRM','SNDK','SBAC','SLB','STX','SRE','NOW','SHW','SPG','SKYD','SWKS','SJM','SW','SNA','SOLV','SO','LUV','SWK','SBUX','STT','STLD','STE','SYK','SMCI','SYF','SNPS','SYY','TMUS','TROW','TTWO','TPR','TRGP','TGT','TEL','TDY','TER','TSLA','TXN','TPL','TXT','TMO','TJX','TKO','TSCO','TT','TDG','TRV','TRMB','TFC','TWLO','TYL','TSN','USB','UBER','UDR','ULTA','UNP','UAL','UPS','URI','UNH','UHS','VLO','VEEV','VTR','VLTO','VRSN','VRSK','VZ','VRTX','VRT','VTRS','VICI','V','VST','VMRK','VMC','WRB','GWW','WAB','WMT','DIS','WM','WAT','WEC','WFC','WELL','WST','WDC','WY','WSM','WMB','WTW','WDAY','WYNN','XEL','XYL','YUM','ZBRA','ZBH','ZTS'],
    '3-7': ['NVDA','AAPL','MSFT','AMZN','GOOGL','SPCX','GOOG','META','AVGO','TSLA','MU','AMD','WMT','ASML','INTC','PLTR','CSCO','COST','AMAT','LRCX','PANW','NFLX','ARM','CRWD','TXN','KLAC','MRVL','SNDK','AMGN','LIN','SHOP','ADI','GILD','QCOM','STX','PEP','TMUS','ISRG','WDC','FTNT','VRTX','BKNG','PDD','ADP','CEG','DDOG','SBUX','LITE','ABNB','SNPS','CDNS','MELI','MAR','ADBE','APP','MRNA','CSX','MNST','DASH','INTU','CTAS','MDLZ','REGN','CMCSA','ROST','ORLY','MPWR','AEP','HON','TER','MSTR','NBIS','ALAB','FAST','NXPI','PCAR','BKR','FANG','HONA','ADSK','PYPL','XEL','CCEP','CRWV','WDAY','TRI','RKLB','KDP','EXC','MCHP','IDXX','TTWO','ODFL','PAYX','FER','ROP','AXON','DXCM','ALNY','GEHC','CPRT'],
    '3-8': ['GS','CAT','MSFT','AMGN','V','UNH','TRV','GOOGL','AAPL','JPM','SHW','AXP','HD','AMZN','JNJ','MCD','NVDA','CRM','IBM','CVX','HON','BA','MMM','PG','MRK','CSCO','WMT','DIS','KO','NKE'],
    '4-50': ['ALL.AX','AMC.AX','ANZ.AX','BHP.AX','BXB.AX','CAR.AX','CBA.AX','COH.AX','COL.AX','CPU.AX','CSL.AX','EVN.AX','FMG.AX','FPH.AX','GMG.AX','IAG.AX','JBH.AX','JHX.AX','LYC.AX','MPL.AX','MQG.AX','NAB.AX','NEM.AX','NST.AX','NWS.AX','ORG.AX','PME.AX','QAN.AX','QBE.AX','REA.AX','RIO.AX','RMD.AX','S32.AX','SCG.AX','SGH.AX','SGP.AX','SIG.AX','SOL.AX','STO.AX','SUN.AX','TCL.AX','TLS.AX','VAS.AX','WBC.AX','WES.AX','WDS.AX','WOW.AX','XRO.AX','XYZ.AX'],
    '4-100': ['CBA.AX','BHP.AX','WBC.AX','ANZ.AX','WES.AX','MQG.AX','NAB.AX','CSL.AX','WDS.AX','FMG.AX','TLS.AX','RIO.AX','GMG.AX','WOW.AX','TCL.AX','QBE.AX','NST.AX','BXB.AX','SIG.AX','COL.AX','ALL.AX','EVN.AX','STO.AX','ORG.AX','REA.AX','S32.AX','LYC.AX','RMD.AX','FPH.AX','SCG.AX','IAG.AX','SUN.AX','SGH.AX','PLS.AX','CPU.AX','SOL.AX','NEM.AX','APA.AX','QAN.AX','WTC.AX','XRO.AX','PME.AX','MPL.AX','TLC.AX','JHX.AX','BSL.AX','AIA.AX','COH.AX','VCX.AX','YAL.AX','ALQ.AX','MIN.AX','ASX.AX','SGP.AX','SHL.AX','LNW.AX','IFT.AX','ORI.AX','RHC.AX','TNE.AX','CHC.AX','GGP.AX','CAR.AX','GPT.AX','AMC.AX','AFI.AX','REH.AX','TPG.AX','ALD.AX','JBH.AX','SFR.AX','WHC.AX','MCY.AX','NXT.AX','PRU.AX','RMS.AX','AZJ.AX','A2M.AX','MGR.AX','GMD.AX','APE.AX','AGL.AX','HUB.AX','ARG.AX','DXS.AX','ALX.AX','IGO.AX','HVN.AX','MEZ.AX','BEN.AX','CDA.AX','EDV.AX','CGF.AX','WGX.AX','DNL.AX','WOR.AX','LTR.AX','GQG.AX','NWL.AX'],
    '3-2': ['AA','AAL','AAON','ACI','ACM','ADC','AEIS','AFG','AGCO','AGNC','AHR','AIT','ALGM','ALK','ALLY','ALSN','ALV','AM','AMG','AMH','AMKR','AN','ANF','APG','APPF','AR','ARMK','ARW','ARWR','ASB','ASH','ATI','ATR','AVAV','AVNT','AVT','AVTR','AXTA','AYI','BAH','BBWI','BC','BCO','BDC','BHF','BILL','BIO','BJ','BKH','BMRN','BRKR','BROS','BRX','BSY','BTSG','BURL','BWA','BWXT','BYD','CACI','CAR','CART','CAVA','CBSH','CBT','CCK','CDE','CDP','CELH','CFR','CG','CGNX','CHDN','CHE','CHH','CHRD','CHWY','CLF','CLH','CMC','CNH','CNM','CNO','CNX','COKE','COLB','COLM','CORT','CR','CRBG','CROX','CRS','CRUS','CSL','CTRE','CTVA','CUBE','CUZ','CVLT','CW','CXT','CYTK','DAR','DBX','DCI','DINO','DKS','DLB','DOCN','DOCS','DOCU','DT','DTM','DUOL','DY','EAT','EEFT','EGP','EHC','ELAN','ELF','ELS','ENS','ENSG','ENTG','EPR','EQH','ESAB','ESNT','EVR','EWBC','EXEL','EXLS','EXP','EXPO','FAF','FBIN','FCFS','FCN','FFIN','FHI','FHN','FIVE','FLG','FLR','FLS','FN','FNB','FND','FNF','FORM','FOUR','FR','FTI','G','GAP','GATX','GBCI','GEF','GGG','GHC','GLPI','GME','GMED','GNTX','GPK','GWRE','GXO','H','HAE','HALO','HGV','HIMS','HL','HLI','HLNE','HOG','HOMB','HQY','HR','HRB','HUBS','HWC','HXL','IBOC','IDA','IDCC','IESC','INGR','IPGP','IRT','ITT','JAZZ','JEF','JLL','KBH','KBR','KD','KEX','KNF','KNSL','KNX','KRC','KRG','KRYS','KTOS','LAD','LAMR','LEA','LECO','LFUS','LIVN','LNTH','LOPE','LPX','LSCC','LSTR','M','MANH','MAT','MEDP','MIDD','MKSI','MLI','MMS','MOG-A','MOH','MORN','MP','MSA','MSM','MTDR','MTG','MTN','MTSI','MTZ','MUR','MUSA','MZTI','NBIX','NEU','NFG','NJR','NLY','NNN','NOV','NOVT','NTNX','NVST','NVT','NWE','NXST','NXT','NYT','OC','OGE','OGS','OHI','OKTA','OLED','OLLI','ONB','ONTO','OPCH','ORA','ORI','OSK','OVV','OZK','PAG','PATH','PB','PBF','PCTY','PEGA','PEN','PFGC','PII','PINS','PK','PLNT','PNFP','POR','POST','PPC','PR','PRI','PSN','PVH','QLYS','R','RBA','RBC','REXR','RGA','RGEN','RGLD','RH','RLI','RMBS','RNR','ROIV','ROKU','RPM','RRC','RRX','RS','RYAN','RYN','SAIA','SAIC','SANM','SARO','SBRA','SCI','SEIC','SF','SFM','SGI','SHC','SIGI','SIRI','SITM','SLAB','SLGN','SLM','SMG','SMTC','SN','SNX','SOLS','SON','SPXC','SR','SSB','SSD','ST','STAG','STRL','STWD','SUI','SWX','SYNA','TCBI','TEX','THC','THG','THO','TKR','TLN','TNL','TOL','TOST','TREX','TRU','TTC','TTEK','TTMI','TXNM','TXRH','UBSI','UFPI','UGI','ULS','UMBF','UNM','USFD','UTHR','VAL','VC','VFC','VIAV','VICR','VLY','VMI','VNO','VNOM','VNT','VOYA','VVV','WAL','WCC','WEX','WFRD','WH','WHR','WING','WLK','WMG','WMS','WPC','WSO','WTFC','WTRG','WTS','WWD','XPO','XRAY','YETI','ZION','AAMI','AAP','AAT','ABCB','ABG','ABM','ABR','ACA','ACAD','ACHC','ACIW','ACLS','ACMR','ACT','ADAM','ADEA','ADIG','ADMA','ADNT','ADT','ADUS','AEO','AESI','AGNT','AGO','AGX','AGYS','AHCO','AIN','AIR','AKR','ALG','ALGT','ALHC','ALKS','ALRM','AMN','AMPH','AMR','AMRX','AMSF','AMTM','ANDE','ANIP','AORT','AOSL','APAM','APLE','APOG','ARCB','ARLO','AROC','ARR','ASO','ASTE','ASTH','ATEN','ATMU','AUB','AVA','AWI','AWR','AX','AZTA','AZZ','BANC','BANF','BANR','BBT','BCC','BCPC','BFAM','BFH','BFS','BGC','BHE','BJRI','BKE','BKU','BL','BLKB','BMI','BNL','BOH','BOOT','BOX','BRC','BTU','BXMT','CACC','CAG','CAKE','CALM','CALX','CALY','CARG','CASH','CATY','CBRL','CBU','CC','CCOI','CCS','CE','CENT','CENTA','CENX','CERT','CFFN','CHCO','CHEF','CLSK','CNK','CNMD','CNR','CNS','CNXC','CNXN','COCO','COHU','COLL','CON','COTY','CPB','CPF','CPK','CRC','CRGY','CRI','CRK','CRSR','CRVL','CSR','CSW','CTS','CUBI','CURB','CVBF','CVCO','CVI','CVSA','CWEN','CWK','CWST','CWT','CXM','CXW','CZR','DAN','DAVE','DBD','DCH','DCOM','DEA','DEI','DFH','DFIN','DGII','DIOD','DLX','DMC','DNOW','DORM','DRH','DV','DXC','DXPE','EBC','ECG','ECPG','EFC','EFOR','EGBN','EIG','EMN','ENOV','ENPH','ENR','ENVA','EPAC','EPAM','EPC','EPRT','ESE','ESI','ETSY','EVTC','EXTR','EYE','EZPW','FA','FBK','FBNC','FBP','FBRT','FCF','FCPT','FELE','FFBC','FG','FHB','FIBK','FIVN','FIZZ','FLO','FMC','FOXF','FRPT','FSS','FTDR','FTRE','FUL','FULT','FUN','GBX','GEO','GFF','GIII','GKOS','GNL','GNW','GO','GOLF','GPI','GPOR','GRBK','GSHD','GT','GTES','GTM','GTY','GVA','HAFC','HASI','HAYW','HCC','HCI','HCSG','HE','HFWA','HIW','HLIT','HMN','HNI','HOPE','HP','HRMY','HSTM','HTH','HTLD','HTO','HUBG','HWKN','HZO','IART','IBP','ICHR','ICUI','IIPR','INDB','INDV','INSP','INSW','INVA','INVX','IOSP','IPAR','IRDM','ITGR','ITRI','IVT','JBGS','JBLU','JBSS','JBTM','JJSF','JOE','JXN','KAI','KALU','KFY','KGS','KLIC','KMPR','KMT','KMX','KN','KNTK','KOP','KRMN','KSS','KTB','KWR','LAUR','LAZ','LBRT','LCII','LEU','LFST','LGIH','LIF','LGND','LKFN','LKQ','LMAT','LNC','LNN','LPG','LQDA','LQDT','LRN','LTC','LTH','LUMN','LW','LXP','LYFT','LZ','LZB','MAC','MAN','MARA','MATW','MATX','MBC','MBGL','MBIN','MC','MCRI','MCY','MD','MDU','MFP','MGEE','MGY','MHK','MHO','MIR','MKTX','MLKN','MMI','MMSI','MPT','MRCY','MRP','MRTN','MSEX','MSGS','MTCH','MTH','MTRN','MTUS','MTX','MWA','MXL','MYRG','NABL','NATL','NAVI','NBHC','NBTB','NE','NEO','NEOG','NGVT','NHC','NHI','NIC','NMIH','NOG','NPK','NPO','NSIT','NSP','NSSC','NTCT','NTST','NWBI','NWL','NWN','NX','NXRT','OFG','OGN','OI','OII','OMCL','OPLN','OSIS','OSW','OTTR','OUT','PAHC','PARR','PAYC','PAYO','PATK','PBH','PBI','PCRX','PDFS','PEB','PECO','PENG','PENN','PFBC','PFS','PGNY','PHIN','PI','PIPR','PJT','PLAB','PLMR','PLUS','PLXS','PMT','POOL','POWI','POWL','PPLI','PRDO','PRG','PRGO','PRGS','PRIM','PRK','PRKS','PRLB','PRSU','PRVA','PSMT','PTCT','PTEN','PTGX','PTON','PZZA','QDEL','QNST','QTWO','RAMP','RAL','RCUS','RDN','RDNT','RELY','RES','REYN','REX','REZI','RHI','RHP','RITM','RNG','RNST','ROAD','ROCK','ROG','RRR','RSI','RUN','RUSHA','RXO','SAFE','SABR','SAFT','SAH','SBCF','SBH','SBSI','SCHL','SCL','SCSC','SDGR','SEDG','SEI','SEZL','SFBS','SFNC','SHAK','SHEN','SHO','SHOO','SIG','SKT','SKY','SKYW','SLG','SLVM','SM','SMP','SMPL','SNDR','SNEX','SONO','SPHR','SPNT','SPSC','SRPT','STAA','STBA','STC','STEP','STRA','SUPN','SXI','SXT','TALO','TBBK','TDC','TDS','TDW','TFIN','TFX','TGTX','THRM','TILE','TMDX','TMP','TNC','TNDM','TPC','TR','TRIP','TRMK','TRN','TRNO','TRST','TRUP','UA','UAA','UCB','UCTT','UE','UFCS','UFPT','UNF','UNFI','UNIT','UPBD','UPWK','URBN','USLM','USPH','UTI','UTL','UVV','VAC','VCEL','VCTR','VCYT','VECO','VGNT','VIR','VIRT','VRRM','VRTS','VSAT','VSEC','VSH','VSNT','VSTS','VSXY','VTOL','VVX','VYX','WABC','WAFD','WAY','WD','WDFC','WEN','WERN','WGO','WHD','WINA','WKC','WLY','WOR','WRBY','WRLD','WS','WSBC','WSC','WSFS','WT','WU','WWW','XHR','XNCR','XPEL','YELP','YOU','ZD','ZWS'],
    '3-4': ['MMM','AOS','ABT','ABBV','ACN','ADBE','AMD','AES','AFL','A','APD','ABNB','AKAM','ALB','ARE','ALGN','ALLE','LNT','ALL','GOOGL','GOOG','MO','AMZN','AMCR','AEE','AEP','AXP','AIG','AMT','AWK','AMP','AME','AMGN','APH','ADI','AON','APA','APO','AAPL','AMAT','APP','APTV','ACGL','ADM','ARES','ANET','AJG','AIZ','T','ATO','ADSK','ADP','AZO','AVY','AXON','BKR','BALL','BAC','BAX','BDX','BRK-B','BBY','TECH','BIIB','BLK','BX','XYZ','BE','BNY','BA','BKNG','BSX','BMY','AVGO','BR','BRO','BF-B','BG','BXP','CHRW','CDNS','CPT','COF','CAH','CCL','CARR','CVNA','CASY','CAT','CBOE','CBRE','CDW','COR','CNC','CNP','CF','CRL','SCHW','CHTR','CVX','CMG','CB','CHD','CIEN','CI','CINF','CTAS','CSCO','C','CFG','CLX','CME','CMS','KO','CTSH','COHR','COIN','CL','CMCSA','FIX','COP','ED','STZ','CEG','COO','CPRT','GLW','CPAY','CSGP','COST','CRH','CRWD','CCI','CSX','CMI','CVS','DHR','DRI','DDOG','DVA','DECK','DE','DELL','DAL','DVN','DXCM','FANG','DLR','DG','DLTR','D','DPZ','DASH','DOV','DOW','DHI','DTE','DUK','DD','ETN','EBAY','ECHO','ECL','EIX','EW','ELV','EME','EMR','ETR','EOG','EQT','EFX','EQIX','ERIE','ESS','EL','EG','EVRG','P','ES','EXC','EXE','EXPE','EXPD','EXR','XOM','FFIV','FDS','FICO','FAST','FRT','FDX','FDXF','FERG','FIS','FITB','FSLR','FE','FISV','FLEX','F','FTNT','FTV','FOXA','FOX','BEN','FCX','GRMN','IT','GE','GEHC','GEV','GEN','GNRC','GD','GIS','GM','GPC','GILD','GPN','GL','GDDY','GS','HAL','HIG','HAS','HCA','DOC','HSIC','HSY','HPE','HLT','HD','HONA','HON','HRL','HST','HWM','HPQ','HUBB','HUM','HBAN','HII','IBM','IEX','IDXX','ITW','ILMN','INCY','IR','PODD','INTC','IBKR','ICE','IFF','IP','INTU','ISRG','IVZ','INVH','IQV','IRM','JBHT','JBL','JKHY','J','JNJ','JCI','JPM','KVUE','KDP','KEY','KEYS','KMB','KIM','KMI','KKR','KLAC','KHC','KR','LHX','LH','LRCX','LVS','LDOS','LEN','LII','LLY','LIN','LYV','LMT','L','LOW','LULU','LITE','LYB','MTB','MPC','MAR','MRSH','MLM','MRVL','MAS','MA','MKC','MCD','MCK','MDT','MRK','META','MET','MTD','MGM','MCHP','MU','MSFT','MAA','MRNA','MDLZ','MPWR','MNST','MCO','MS','MOS','MSI','MSCI','NDAQ','NTAP','NFLX','NEM','NWSA','NWS','NEE','NKE','NI','NDSN','NSC','NTRS','NOC','NCLH','NRG','NUE','NVDA','NVR','NXPI','ORLY','OXY','ODFL','OMC','ON','OKE','ORCL','OTIS','PCAR','PKG','PLTR','PANW','PH','PAYX','PYPL','PNR','PEP','PFE','PCG','PM','PSX','PNW','PNC','PPG','PPL','PFG','PG','PGR','PLD','PRU','PEG','PTC','PSA','PHM','PWR','QCOM','DGX','Q','RL','RJF','RDDT','RTX','O','REG','REGN','RF','RSG','RMD','RVTY','HOOD','ROK','ROL','ROP','ROST','RCL','SPGI','CRM','SNDK','SBAC','SLB','STX','SRE','NOW','SHW','SPG','SKYD','SWKS','SJM','SW','SNA','SOLV','SO','LUV','SWK','SBUX','STT','STLD','STE','SYK','SMCI','SYF','SNPS','SYY','TMUS','TROW','TTWO','TPR','TRGP','TGT','TEL','TDY','TER','TSLA','TXN','TPL','TXT','TMO','TJX','TKO','TSCO','TT','TDG','TRV','TRMB','TFC','TWLO','TYL','TSN','USB','UBER','UDR','ULTA','UNP','UAL','UPS','URI','UNH','UHS','VLO','VEEV','VTR','VLTO','VRSN','VRSK','VZ','VRTX','VRT','VTRS','VICI','V','VST','VMRK','VMC','WRB','GWW','WAB','WMT','DIS','WM','WAT','WEC','WFC','WELL','WST','WDC','WY','WSM','WMB','WTW','WDAY','WYNN','XEL','XYL','YUM','ZBRA','ZBH','ZTS','AA','AAL','AAON','ACI','ACM','ADC','AEIS','AFG','AGCO','AGNC','AHR','AIT','ALGM','ALK','ALLY','ALSN','ALV','AM','AMG','AMH','AMKR','AN','ANF','APG','APPF','AR','ARMK','ARW','ARWR','ASB','ASH','ATI','ATR','AVAV','AVNT','AVT','AVTR','AXTA','AYI','BAH','BBWI','BC','BCO','BDC','BHF','BILL','BIO','BJ','BKH','BMRN','BRKR','BROS','BRX','BSY','BTSG','BURL','BWA','BWXT','BYD','CACI','CAR','CART','CAVA','CBSH','CBT','CCK','CDE','CDP','CELH','CFR','CG','CGNX','CHDN','CHE','CHH','CHRD','CHWY','CLF','CLH','CMC','CNH','CNM','CNO','CNX','COKE','COLB','COLM','CORT','CR','CRBG','CROX','CRS','CRUS','CSL','CTRE','CTVA','CUBE','CUZ','CVLT','CW','CXT','CYTK','DAR','DBX','DCI','DINO','DKS','DLB','DOCN','DOCS','DOCU','DT','DTM','DUOL','DY','EAT','EEFT','EGP','EHC','ELAN','ELF','ELS','ENS','ENSG','ENTG','EPR','EQH','ESAB','ESNT','EVR','EWBC','EXEL','EXLS','EXP','EXPO','FAF','FBIN','FCFS','FCN','FFIN','FHI','FHN','FIVE','FLG','FLR','FLS','FN','FNB','FND','FNF','FORM','FOUR','FR','FTI','G','GAP','GATX','GBCI','GEF','GGG','GHC','GLPI','GME','GMED','GNTX','GPK','GWRE','GXO','H','HAE','HALO','HGV','HIMS','HL','HLI','HLNE','HOG','HOMB','HQY','HR','HRB','HUBS','HWC','HXL','IBOC','IDA','IDCC','IESC','INGR','IPGP','IRT','ITT','JAZZ','JEF','JLL','KBH','KBR','KD','KEX','KNF','KNSL','KNX','KRC','KRG','KRYS','KTOS','LAD','LAMR','LEA','LECO','LFUS','LIVN','LNTH','LOPE','LPX','LSCC','LSTR','M','MANH','MAT','MEDP','MIDD','MKSI','MLI','MMS','MOG-A','MOH','MORN','MP','MSA','MSM','MTDR','MTG','MTN','MTSI','MTZ','MUR','MUSA','MZTI','NBIX','NEU','NFG','NJR','NLY','NNN','NOV','NOVT','NTNX','NVST','NVT','NWE','NXST','NXT','NYT','OC','OGE','OGS','OHI','OKTA','OLED','OLLI','ONB','ONTO','OPCH','ORA','ORI','OSK','OVV','OZK','PAG','PATH','PB','PBF','PCTY','PEGA','PEN','PFGC','PII','PINS','PK','PLNT','PNFP','POR','POST','PPC','PR','PRI','PSN','PVH','QLYS','R','RBA','RBC','REXR','RGA','RGEN','RGLD','RH','RLI','RMBS','RNR','ROIV','ROKU','RPM','RRC','RRX','RS','RYAN','RYN','SAIA','SAIC','SANM','SARO','SBRA','SCI','SEIC','SF','SFM','SGI','SHC','SIGI','SIRI','SITM','SLAB','SLGN','SLM','SMG','SMTC','SN','SNX','SOLS','SON','SPXC','SR','SSB','SSD','ST','STAG','STRL','STWD','SUI','SWX','SYNA','TCBI','TEX','THC','THG','THO','TKR','TLN','TNL','TOL','TOST','TREX','TRU','TTC','TTEK','TTMI','TXNM','TXRH','UBSI','UFPI','UGI','ULS','UMBF','UNM','USFD','UTHR','VAL','VC','VFC','VIAV','VICR','VLY','VMI','VNO','VNOM','VNT','VOYA','VVV','WAL','WCC','WEX','WFRD','WH','WHR','WING','WLK','WMG','WMS','WPC','WSO','WTFC','WTRG','WTS','WWD','XPO','XRAY','YETI','ZION','AAMI','AAP','AAT','ABCB','ABG','ABM','ABR','ACA','ACAD','ACHC','ACIW','ACLS','ACMR','ACT','ADAM','ADEA','ADIG','ADMA','ADNT','ADT','ADUS','AEO','AESI','AGNT','AGO','AGX','AGYS','AHCO','AIN','AIR','AKR','ALG','ALGT','ALHC','ALKS','ALRM','AMN','AMPH','AMR','AMRX','AMSF','AMTM','ANDE','ANIP','AORT','AOSL','APAM','APLE','APOG','ARCB','ARLO','AROC','ARR','ASO','ASTE','ASTH','ATEN','ATMU','AUB','AVA','AWI','AWR','AX','AZTA','AZZ','BANC','BANF','BANR','BBT','BCC','BCPC','BFAM','BFH','BFS','BGC','BHE','BJRI','BKE','BKU','BL','BLKB','BMI','BNL','BOH','BOOT','BOX','BRC','BTU','BXMT','CACC','CAG','CAKE','CALM','CALX','CALY','CARG','CASH','CATY','CBRL','CBU','CC','CCOI','CCS','CE','CENT','CENTA','CENX','CERT','CFFN','CHCO','CHEF','CLSK','CNK','CNMD','CNR','CNS','CNXC','CNXN','COCO','COHU','COLL','CON','COTY','CPB','CPF','CPK','CRC','CRGY','CRI','CRK','CRSR','CRVL','CSR','CSW','CTS','CUBI','CURB','CVBF','CVCO','CVI','CVSA','CWEN','CWK','CWST','CWT','CXM','CXW','CZR','DAN','DAVE','DBD','DCH','DCOM','DEA','DEI','DFH','DFIN','DGII','DIOD','DLX','DMC','DNOW','DORM','DRH','DV','DXC','DXPE','EBC','ECG','ECPG','EFC','EFOR','EGBN','EIG','EMN','ENOV','ENPH','ENR','ENVA','EPAC','EPAM','EPC','EPRT','ESE','ESI','ETSY','EVTC','EXTR','EYE','EZPW','FA','FBK','FBNC','FBP','FBRT','FCF','FCPT','FELE','FFBC','FG','FHB','FIBK','FIVN','FIZZ','FLO','FMC','FOXF','FRPT','FSS','FTDR','FTRE','FUL','FULT','FUN','GBX','GEO','GFF','GIII','GKOS','GNL','GNW','GO','GOLF','GPI','GPOR','GRBK','GSHD','GT','GTES','GTM','GTY','GVA','HAFC','HASI','HAYW','HCC','HCI','HCSG','HE','HFWA','HIW','HLIT','HMN','HNI','HOPE','HP','HRMY','HSTM','HTH','HTLD','HTO','HUBG','HWKN','HZO','IART','IBP','ICHR','ICUI','IIPR','INDB','INDV','INSP','INSW','INVA','INVX','IOSP','IPAR','IRDM','ITGR','ITRI','IVT','JBGS','JBLU','JBSS','JBTM','JJSF','JOE','JXN','KAI','KALU','KFY','KGS','KLIC','KMPR','KMT','KMX','KN','KNTK','KOP','KRMN','KSS','KTB','KWR','LAUR','LAZ','LBRT','LCII','LEU','LFST','LGIH','LIF','LGND','LKFN','LKQ','LMAT','LNC','LNN','LPG','LQDA','LQDT','LRN','LTC','LTH','LUMN','LW','LXP','LYFT','LZ','LZB','MAC','MAN','MARA','MATW','MATX','MBC','MBGL','MBIN','MC','MCRI','MCY','MD','MDU','MFP','MGEE','MGY','MHK','MHO','MIR','MKTX','MLKN','MMI','MMSI','MPT','MRCY','MRP','MRTN','MSEX','MSGS','MTCH','MTH','MTRN','MTUS','MTX','MWA','MXL','MYRG','NABL','NATL','NAVI','NBHC','NBTB','NE','NEO','NEOG','NGVT','NHC','NHI','NIC','NMIH','NOG','NPK','NPO','NSIT','NSP','NSSC','NTCT','NTST','NWBI','NWL','NWN','NX','NXRT','OFG','OGN','OI','OII','OMCL','OPLN','OSIS','OSW','OTTR','OUT','PAHC','PARR','PAYC','PAYO','PATK','PBH','PBI','PCRX','PDFS','PEB','PECO','PENG','PENN','PFBC','PFS','PGNY','PHIN','PI','PIPR','PJT','PLAB','PLMR','PLUS','PLXS','PMT','POOL','POWI','POWL','PPLI','PRDO','PRG','PRGO','PRGS','PRIM','PRK','PRKS','PRLB','PRSU','PRVA','PSMT','PTCT','PTEN','PTGX','PTON','PZZA','QDEL','QNST','QTWO','RAMP','RAL','RCUS','RDN','RDNT','RELY','RES','REYN','REX','REZI','RHI','RHP','RITM','RNG','RNST','ROAD','ROCK','ROG','RRR','RSI','RUN','RUSHA','RXO','SAFE','SABR','SAFT','SAH','SBCF','SBH','SBSI','SCHL','SCL','SCSC','SDGR','SEDG','SEI','SEZL','SFBS','SFNC','SHAK','SHEN','SHO','SHOO','SIG','SKT','SKY','SKYW','SLG','SLVM','SM','SMP','SMPL','SNDR','SNEX','SONO','SPHR','SPNT','SPSC','SRPT','STAA','STBA','STC','STEP','STRA','SUPN','SXI','SXT','TALO','TBBK','TDC','TDS','TDW','TFIN','TFX','TGTX','THRM','TILE','TMDX','TMP','TNC','TNDM','TPC','TR','TRIP','TRMK','TRN','TRNO','TRST','TRUP','UA','UAA','UCB','UCTT','UE','UFCS','UFPT','UNF','UNFI','UNIT','UPBD','UPWK','URBN','USLM','USPH','UTI','UTL','UVV','VAC','VCEL','VCTR','VCYT','VECO','VGNT','VIR','VIRT','VRRM','VRTS','VSAT','VSEC','VSH','VSNT','VSTS','VSXY','VTOL','VVX','VYX','WABC','WAFD','WAY','WD','WDFC','WEN','WERN','WGO','WHD','WINA','WKC','WLY','WOR','WRBY','WRLD','WS','WSBC','WSC','WSFS','WT','WU','WWW','XHR','XNCR','XPEL','YELP','YOU','ZD','ZWS'],  # S&P 1500 (S&P 500 + S&P 400 + S&P 600)
    '3-5': ["A", "AAL", "AAON", "AAPL", "ABT", "ACGL", "ACHC", "ACI", "ACN", "ADBE", "ADC", "ADI", "ADM", "ADP", "ADSK", "ADT", "AEP", "AES", "AFG", "AFRM", "AGCO", "AGNC", "AGO", "AIG", "AIT", "AIZ", "AJG", "AKAM", "ALAB", "ALB", "ALGM", "ALGN", "ALK", "ALL", "ALLE", "ALLY", "ALNY", "ALSN", "AM", "AMAT", "AMD", "AMG", "AMH", "AMKR", "AMP", "AMT", "AMTM", "AN", "ANET", "AON", "AOS", "APA", "APD", "APG", "APH", "APO", "APP", "APPF", "AR", "ARE", "ARES", "ARMK", "ARW", "AS", "ASH", "ASTS", "ATI", "ATO", "ATR", "AU", "AUR", "AVB", "AVGO", "AVTR", "AVY", "AWI", "AWK", "AXON", "AXP", "AXS", "AYI", "AZO", "BAC", "BAH", "BALL", "BAM", "BAX", "BBWI", "BBY", "BC", "BDX", "BEN", "BEPC", "BF-B", "BFAM", "BG", "BHF", "BILL", "BIO", "BIRK", "BJ", "BKNG", "BKR", "BLDR", "BLK", "BMRN", "BMY", "BOKF", "BPOP", "BR", "BRBR", "BRK-B", "BRO", "BROS", "BRX", "BSX", "BSY", "BURL", "BWA", "BWXT", "BX", "BXP", "BYD", "C", "CACC", "CACI", "CAG", "CAH", "CAI", "CAR", "CARR", "CART", "CASY", "CAT", "CAVA", "CB", "CBOE", "CBRE", "CBSH", "CCI", "CCK", "CCL", "CDNS", "CDW", "CE", "CEG", "CELH", "CERT", "CF", "CFG", "CFR", "CG", "CGNX", "CHD", "CHDN", "CHE", "CHH", "CHRD", "CHRW", "CHTR", "CINF", "CL", "CLF", "CLH", "CLVT", "CMCSA", "CME", "CMG", "CMI", "CMS", "CNA", "CNC", "CNH", "CNM", "CNP", "CNXC", "COF", "COHR", "COIN", "COKE", "COLB", "COLD", "COLM", "COO", "COP", "COR", "CORT", "CPB", "CPNG", "CPT", "CR", "CRH", "CRL", "CRM", "CRS", "CRUS", "CRWD", "CSGP", "CSL", "CSX", "CTSH", "CTVA", "CUBE", "CUZ", "CVNA", "CVS", "CVX", "CW", "CWEN", "CXT", "CZR", "Coty", "D", "DAL", "DAR", "DASH", "DBX", "DCI", "DDOG", "DDS", "DE", "DECK", "DELL", "DG", "DGX", "DHI", "DHR", "DINO", "DIS", "DJT", "DKNG", "DKS", "DLB", "DLR", "DLTR", "DOC", "DOCS", "DOCU", "DOV", "DOW", "DPZ", "DRI", "DRS", "DT", "DTE", "DTM", "DUK", "DUOL", "DV", "DVN", "DXC", "EA", "ECG", "ED", "EEFT", "EFX", "EG", "EGP", "EHC", "EIX", "EL", "ELF", "ELS", "ELV", "EMN", "EMR", "ENPH", "ENTG", "EOG", "EPAM", "EPR", "EQH", "EQIX", "EQR", "EQT", "ES", "ESAB", "ESI", "ESS", "ESTC", "ETN", "ETR", "EVR", "EW", "EWBC", "EXE", "EXEL", "EXLS", "EXP", "EXPD", "EXPE", "EXR", "Etsy", "F", "FAF", "FANG", "FAST", "FBIN", "FCN", "FCNCA", "FCX", "FDS", "FE", "FERG", "FFIV", "FHB", "FHN", "FICO", "FIS", "FITB", "FIVE", "FIX", "FLEX", "FLO", "FLS", "FLUT", "FMC", "FNB", "FND", "FNF", "FOX", "FOXA", "FR", "FRHC", "FRPT", "FRT", "FSLR", "FTAI", "FTI", "FTNT", "FTV", "FWONA", "FWONK", "FedEx", "G", "GAP", "GD", "GDDY", "GE", "GEHC", "GEN", "GEV", "GFS", "GGG", "GILD", "GIS", "GL", "GLIBA", "GLIBK", "GLOB", "GLPI", "GLW", "GM", "GME", "GMED", "GNRC", "GOOG", "GOOGL", "GPC", "GPK", "GPN", "GS", "GTES", "GTM", "GWRE", "GWW", "GXO", "H", "HAL", "HALO", "HAYW", "HBAN", "HCA", "HD", "HEI", "HHH", "HIG", "HII", "HIW", "HLI", "HLNE", "HLT", "HOG", "HON", "HOOD", "HPE", "HPQ", "HR", "HRB", "HRL", "HSIC", "HST", "HSY", "HUBB", "HUBS", "HUN", "HWM", "IBKR", "IBM", "ICE", "IDA", "IDXX", "IEX", "IFF", "ILMN", "INGM", "INGR", "INSP", "INVH", "IONS", "IOT", "IP", "IPGP", "IR", "IRDM", "IRM", "ISRG", "IT", "ITT", "ITW", "IVZ", "J", "JAZZ", "JBHT", "JCI", "JEF", "JHX", "JKHY", "JLL", "JNJ", "JPM", "KBR", "KD", "KDP", "KEX", "KEY", "KEYS", "KHC", "KIM", "KKR", "KLAC", "KMB", "KMI", "KMPR", "KNSL", "KNX", "KO", "KRC", "KRMN", "L", "LAD", "LAMR", "LBRDA", "LBRDK", "LBTYA", "LBTYK", "LCID", "LEA", "LECO", "LEN", "LFUS", "LH", "LHX", "LII", "LIN", "LINE", "LITE", "LKQ", "LLY", "LLYVA", "LLYVK", "LMT", "LNC", "LNG", "LNT", "LOAR", "LOPE", "LOW", "LPLA", "LPX", "LRCX", "LSCC", "LSTR", "LULU", "LUV", "LVS", "LW", "LYB", "LYV", "Lyft", "M", "MA", "MAA", "MAN", "MANH", "MAR", "MCD", "MCHP", "MCK", "MCO", "MDB", "MDLZ", "MDT", "MDU", "MEDP", "MET", "META", "MGM", "MHK", "MIDD", "MKC", "MKSI", "MKTX", "MLI", "MLM", "MNST", "MOH", "MORN", "MOS", "MP", "MPC", "MPWR", "MRK", "MRNA", "MRP", "MRVL", "MS", "MSA", "MSCI", "MSFT", "MSGS", "MSI", "MSM", "MSTR", "MTB", "MTCH", "MTD", "MTDR", "MTG", "MTN", "MTSI", "MU", "MUSA", "NBIX", "NCLH", "NDAQ", "NDSN", "NEE", "NEM", "NET", "NEU", "NFG", "NFLX", "NI", "NIQ", "NKE", "NLY", "NNN", "NOC", "NOV", "NOW", "NRG", "NSC", "NTNX", "NTRS", "NVR", "NVST", "NVT", "NWL", "NWS", "NWSA", "NXST", "NYT", "O", "OC", "ODFL", "OGE", "OGN", "OHI", "OKTA", "OLED", "OLLI", "OLN", "OMC", "OMF", "ON", "ONON", "ONTO", "ORCL", "ORI", "ORLY", "OSK", "OTIS", "OVV", "OWL", "OXY", "OZK", "PAG", "PANW", "PAYX", "PB", "PCG", "PCOR", "PCTY", "PEG", "PEGA", "PEN", "PENN", "PEP", "PFG", "PFGC", "PG", "PGR", "PH", "PHM", "PINS", "PK", "PKG", "PLD", "PLNT", "PLTR", "PM", "PNC", "PNFP", "PNR", "PNW", "PODD", "POOL", "POST", "PPC", "PPG", "PPL", "PR", "PRGO", "PRI", "PRMB", "PRU", "PSA", "PSN", "PSX", "PTC", "PVH", "PWR", "QCOM", "QS", "QSR", "QXO", "RAL", "RARE", "RBA", "RBC", "RBLX", "RCL", "REG", "REGN", "REXR", "REYN", "RF", "RGA", "RGEN", "RGLD", "RH", "RHI", "RITM", "RJF", "RKLB", "RKT", "RL", "RLI", "RNG", "RNR", "ROIV", "ROK", "ROKU", "ROL", "ROP", "ROST", "RPM", "RPRX", "RRC", "RRX", "RS", "RSG", "RTX", "RVMD", "RVTY", "RYAN", "RYN", "S", "SAIC", "SAIL", "SAM", "SARO", "SBAC", "SBUX", "SCCO", "SCHW", "SCI", "SEB", "SEIC", "SFD", "SFM", "SGI", "SHC", "SHW", "SIRI", "SITE", "SJM", "SLB", "SLGN", "SLM", "SMCI", "SMG", "SMMT", "SN", "SNA", "SNDK", "SNDR", "SNOW", "SNPS", "SNX", "SO", "SOLV", "SPG", "SPGI", "SPOT", "SRPT", "SSB", "SSD", "SSNC", "ST", "STAG", "STLD", "STT", "STWD", "STZ", "SUI", "SW", "SWK", "SWKS", "SYF", "SYK", "Saia", "SoFi", "T", "TAP", "TDC", "TDG", "TDY", "TEAM", "TECH", "TEM", "TER", "TFC", "TFSL", "TFX", "TGT", "THC", "THG", "THO", "TIGO", "TJX", "TKO", "TKR", "TLN", "TMO", "TMUS", "TNL", "TOL", "TOST", "TPG", "TPL", "TPR", "TREX", "TRGP", "TRMB", "TROW", "TRU", "TRV", "TSCO", "TSLA", "TSN", "TT", "TTC", "TTD", "TTEK", "TTWO", "TW", "TXN", "TXRH", "TXT", "TYL", "U", "UA", "UAA", "UAL", "UDR", "UGI", "UHS", "UI", "ULTA", "UNH", "UNP", "UPS", "URI", "USB", "USFD", "UTHR", "UWMC", "Uber", "V", "VEEV", "VFC", "VICI", "VIK", "VIRT", "VKTX", "VLO", "VLTO", "VMC", "VMI", "VNO", "VNOM", "VNT", "VOYA", "VRSK", "VRSN", "VRTX", "VST", "VTR", "VTRS", "VVV", "VZ", "W", "WAL", "WAT", "WBD", "WBS", "WCC", "WDAY", "WDC", "WEC", "WELL", "WEN", "WEX", "WFC", "WFRD", "WH", "WHR", "WING", "WLK", "WM", "WMB", "WMS", "WMT", "WPC", "WRB", "WSC", "WSM", "WST", "WTFC", "WTM", "WTRG", "WTW", "WU", "WWD", "WY", "WYNN", "XEL", "XOM", "XP", "XPO", "XRAY", "XYL", "XYZ", "YETI", "YUM"],
    '3-6': ["CRDO", "IONQ", "BE", "KTOS", "OKLO", "FN", "CDE", "NXT", "AVAV", "RGTI", "RMBS", "HIMS", "STRL", "ENSG", "IDCC", "SPXC", "QBTS", "UMBF", "MDGL", "BBIO", "CVLT", "JOBY", "DY", "MOD", "WTS", "HQY", "ONB", "PRIM", "CTRE", "JBTM", "GH", "HL", "FLR", "FSS", "ZWS", "JXN", "MARA", "AEIS", "RIOT", "CMC", "AHR", "VRNS", "CYTK", "SOUN", "SITM", "SMTC", "GATX", "LRN", "SANM", "ORA", "GBCI", "LUMN", "TTMI", "PIPR", "CRSP", "ESNT", "EPRT", "REZI", "ROAD", "FCFS", "TRNO", "UEC", "IBP", "CWST", "APLD", "EAT", "UFPI", "GPI", "ACIW", "ITRI", "ACHR", "RHP", "TXNM", "IRTC", "ESE", "LEU", "HOMB", "RDNT", "HWC", "BMI", "TGTX", "MIR", "UBSI", "BOOT", "MTH", "VLY", "MMS", "CORZ", "BIPC", "SWX", "FTDR", "RYTM", "ALKS", "SIGI", "AUB", "SMR", "ABG", "KRG", "BCO", "PTCT", "ABCB", "AXSM", "NPO", "MMSI", "SSRM", "SR", "GVA", "BCPC", "QLYS", "NJR", "RDN", "OGS", "SNEX", "PI", "POR", "GKOS", "BDC", "MAC", "PCVX", "OPCH", "AX", "STNE", "BOX", "KTB", "CNX", "STEP", "FFIN", "RNA", "KRYS", "ACA", "URBN", "CNR", "CVCO", "UPST", "SKY", "ENS", "WK", "SBRA", "SLG", "CWAN", "BKH", "MGY", "ASB", "SLAB", "KBH", "MRCY", "PECO", "DORM", "CALM", "CLSK", "SFBS", "MC", "WAY", "CSW", "ARWR", "QTWO", "AROC", "PJT", "KNF", "CBT", "SKYW", "HRI", "LAUR", "ANF", "MWA", "RUN", "OSIS", "SPSC", "MUR", "PLXS", "SIG", "GLNG", "TDS", "VRRM", "SXT", "TCBI", "TMDX", "CNO", "IRT", "MHO", "FELE", "SKT", "IBOC", "PTGX", "GHC", "HASI", "OSCR", "CRNX", "UCB", "AAP", "LTH", "GNW", "NOVT", "ATMU", "HUT", "SHAK", "CIFR", "NHI", "VSAT", "EBC", "PFSI", "NUVL", "CALX", "UUUU", "KFY", "AGX", "BTU", "LNTH", "ZETA", "NE", "TENB", "HWKN", "ITGR", "FLG", "BNL", "COMP", "CRC", "IESC", "ASO", "NWE", "AMBA", "KAI", "FBP", "PL", "TBBK", "RNST", "LGND", "EXPO", "MZTI", "PATK", "INDB", "TEX", "VSEC", "BGC", "HCC", "VC", "ADMA", "FULT", "PII", "CDP", "WULF", "PTON", "NSIT", "RUSHA", "MATX", "AZZ", "FUL", "VAL", "CARG", "CATY", "MYRG", "EOSE", "PSMT", "PBH", "WSFS", "BXMT", "OTTR", "PLUG", "CBU", "FORM", "PRM", "CPK", "WSBC", "ACLS", "RRR", "AVNT", "MGEE", "AIR", "GFF", "LMND", "XENE", "PLMR", "GPOR", "BCC", "AVA", "POWL", "NMIH", "ICUI", "NG", "BKU", "MIRM", "CNK", "NATL", "ABM", "VCTR", "SRRK", "FIBK", "SM", "NMRK", "VIAV", "MGRC", "MGNI", "INDV", "KYMR", "PRVA", "LIVN", "VCYT", "WD", "ENVA", "LXP", "APLE", "TPC", "SFNC", "AEO", "APAM", "GEO", "AKR", "CBZ", "EXTR", "RIG", "BTSG", "AWR", "INOD", "RELY", "QUBT", "BL", "ACAD", "CWT", "DAN", "DOCN", "YOU", "WDFC", "BANF", "SYNA", "UE", "GENI", "WRBY", "OUT", "WHD", "SBCF", "RXO", "AGYS", "TDW", "SUPN", "AMSC", "SXI", "CAKE", "BOH", "MTRN", "PBF", "HGV", "UNF", "CVBF", "HURN", "STNG", "TOWN", "ALRM", "CPRI", "CC", "FFBC", "SHOO", "FCPT", "BEAM", "DIOD", "TIC", "BLKB", "FBK", "UNFI", "BUR", "CON", "PRK", "PFS", "WAFD", "GRBK", "HAE", "NOG", "ALHC", "FRSH", "PRDO", "KGS", "OII", "PINC", "LCII", "TARS", "MCY", "EYE", "ARQT", "IVT", "TRMK", "SMPL", "TRN", "CURB", "AGIO", "INTA", "FUN", "UPWK", "AI", "EPAC", "CGON", "GOLF", "HP", "BRZE", "WGS", "FRME", "CSTM", "XMTR", "POWI", "BANR", "CWK", "SGHC", "ACMR", "IDYA", "PHIN", "BANC", "QDEL", "ATKR", "HNI", "WWW", "EVTC", "TVTX", "ADPT", "FBNC", "KLIC", "CRVL", "EFSC", "ADNT", "NBTB", "BBAI", "CXW", "ADUS", "DEI", "KN", "NGVT", "HUBG", "GSAT", "DBRG", "STC", "NTLA", "OI", "RXRX", "LBRT", "DNLI", "CHEF", "GRAL", "BRSL", "STRA", "BBT", "SONO", "AVPT", "PRGS", "MQ", "SDRL", "ALG", "OSW", "ABR", "MTX", "GT", "AMR", "ROCK", "BUSE", "HCI", "BWIN", "OFG", "YELP", "IOSP", "PLUS", "HE", "BKD", "DK", "TNET", "CUBI", "VSH", "ENVX", "COGT", "VAC", "DAVE", "ADEA", "VECO", "JOE", "PTEN", "COCO", "NTCT", "GTX", "HMN", "KWR", "INSW", "MSGE", "CASH", "SPHR", "CNS", "PRCT", "TRIP", "SYBT", "HLMN", "SHO", "BKE", "TWST", "CCOI", "LMAT", "BATRK", "KSS", "NTB", "PARR", "NIC", "VYX", "NWBI", "NWN", "NNI", "FIVN", "NSP", "WOR", "ENOV", "LIF", "GSHD", "KNTK", "RAMP", "PCT", "HLIO", "FCF", "ICFI", "PAGS", "NTST", "DRH", "IPAR", "RSI", "ARR", "MBC", "BLBD", "ARLO", "CHCO", "ACVA", "PAYO", "CLDX", "LTC", "DXPE", "TPB", "MNKD", "ATRC", "ENR", "CCS", "SKWD", "SBH", "SEI", "WLY", "ALKT", "WT", "SGRY", "KMT", "TILE", "MRX", "ZD", "DX", "GNL", "ANIP", "TGLS", "VERX", "TRUP", "ARCB", "FLYW", "AIN", "DNOW", "ATEC", "IIPR", "BTDR", "VCEL", "MLYS", "LKFN", "CENX", "AMRX", "PPTA", "CRK", "PZZA", "SLVM", "CRGY", "OCUL", "JBLU", "AGM", "COUR", "AORT", "NBHC", "NHC", "GEF", "PGNY", "BCRX", "GO", "WERN", "PAR", "IRON", "WINA", "AAOI", "LNN", "BELFB", "ROG", "PENG", "HROW", "TNC", "HTH", "VERA", "CECO", "TDOC", "ELME", "LASR", "SHLS", "DHT", "DBD", "PRKS", "JJSF", "SOC", "VRDN", "HTO", "NSSC", "UFPT", "UTI", "ARI", "CELC", "MD", "CNMD", "PLAB", "CTRI", "OUST", "SPNT", "WKC", "IMAX", "PGY", "NVCR", "NVAX", "LZB", "VITL", "USLM", "STBA", "CCB", "CENTA", "ATRO", "LQDA", "DFIN", "GTY", "PD", "BHVN", "OMCL", "BFH", "GBX", "XHR", "JBGS", "ALIT", "BHE", "GABC", "AMC", "STAA", "TCBK", "DYN", "JBI", "PRCH", "UVV", "PBI", "PEB", "DGII", "ANDE", "MCRI", "ATEN", "ARRY", "SEZL", "LION", "MXL", "TXG", "FUBO", "AUPH", "BLX", "SNDX", "PWP", "HOPE", "UCTT", "PHR", "DCO", "SPB", "WLDN", "LADR", "NNE", "CRAI", "USPH", "APGE", "AZTA", "VRTS", "XERS", "KALU", "CLMT", "AAMI", "PRG", "NEOG", "QCRH", "NN", "FSLY", "TRS", "ARDX", "VRNT", "LUNR", "LOB", "XPRO", "EFC", "APPN", "LZ", "HCSG", "WABC", "SDGR", "DCOM", "MLKN", "TNK", "FA", "UPBD", "HLIT", "RPD", "PRLB", "CNOB", "LEG", "WMK", "AMRC", "USD", "ASAN", "HRMY", "AMPX", "CVI", "SMA", "SAH", "NEO", "CTS", "TALO", "UMH", "VICR", "IMVT", "SRCE", "ASTH", "ACT", "VVX", "BFC", "PCRX", "PMT", "ASTE", "HG", "BTBT", "STOK", "PDM", "NVTS", "INVA", "RLJ", "ESRT", "BBSI", "COLL", "CIM", "TFIN", "AAT", "LGIH", "TWO", "LPG", "THRM", "REAL", "CRI", "IE", "CNNE", "FOXF", "GIII", "PEBO", "ROOT", "WS", "SCL", "VTOL", "LILAK", "OCFC", "SAFT", "EIG", "ECVT", "CDRE", "OBK", "AIV", "TSHA", "CLOV", "METC", "IMKTA", "HPP", "EWTX", "CSR", "FLNC", "WTTR", "PRAX", "BLFS", "CBRL", "RCAT", "AMPH", "CWH", "MFA", "DHC", "BV", "NAVI", "AHCO", "CMPR", "GRC", "ECPG", "SCSC", "LMB", "DRVN", "DOLE", "EPC", "APOG", "IART", "DEA", "MSEX", "FBRT", "NTGR", "AMLX", "WGO", "EVH", "NUVB", "COHU", "REX", "PAX", "AEHR", "JANX", "RZLV", "RCUS", "AMPL", "SFL", "HLX", "FIZZ", "ORC", "MVST", "NPKI", "TMP", "NVRI", "SAFE", "HLF", "TNDM", "NEXT", "CTBI", "FTRE", "IMNM", "CABO", "AESI", "UTZ", "ALGT", "DLX", "EVLV", "YEXT", "RVLV", "CXM", "UVSP", "PNTG", "SMP", "ZYME", "TDUP", "SG", "FMBH", "ERII", "BY", "MBIN", "EMBC", "TRVI", "QNST", "UNIT", "XNCR", "SBSI", "XPEL", "INDI", "ELVN", "OSBC", "HFWA", "PDFS", "AMSF", "IDT", "CDNA", "PAHC", "MDXG", "RWT", "KOS", "SYRE", "BBUC", "BHRB", "DEC", "EYPT", "IAS", "WVE", "HTZ", "AXGN", "LENZ", "FLNG", "RUM", "DAKT", "DFH", "CRMD", "BBNX", "AVXL", "BBW", "GBTG", "TR", "IIIV", "CFFN", "HAFC", "PRSU", "BKSY", "GERN", "ARIS", "MATW", "MTAL", "KE", "AMN", "KURA", "ESQ", "BLND", "UTL", "NXRT", "NBN", "MBWM", "BDN", "HBNC", "TTI", "SXC", "MMI", "CNXN", "LFST", "FWRG", "GDOT", "INVX", "UVE", "BRSP", "TREE", "MCB", "IIIN", "CARS", "RZLT", "CPF", "ICHR", "UAMY", "RGR", "BZH", "PLOW", "AMTB", "ADTN", "MYGN", "RLAY", "BORR", "NRIX", "PFBC", "AOSL", "AKBA", "ASPI", "FG", "APEI", "CCNE", "NX", "GCT", "ABUS", "CMP", "NAT", "IBCP", "SABR", "LINC", "SHEN", "APPS", "TRST", "HSTM", "CLPT", "ETD", "HTB", "GOGO", "UFCS", "VTS", "OLMA", "CSV", "CEVA", "AIOT", "ANGI", "BFST", "ORIC", "HIPO", "BJRI", "BBBY", "FIGS", "SPT", "THFF", "TRNS", "ALNT", "PSIX", "AMAL", "EVGO", "URGN", "RC", "CSTL", "CAC", "PACS", "ZGN", "MTUS", "DNA", "LQDT", "RBCAA", "CCBG", "NBBK", "LYTS", "EQBK", "OPK", "TRTX", "NBR", "CPS", "INN", "HOV", "MYE", "STGW", "ANAB", "EU", "ORRF", "NESR", "UPB", "BLMN", "EVER", "DNTH", "PRAA", "CMCL", "ARVN", "ODC", "MATV", "MBUU", "GHM", "SPRY", "NPK", "ADAM", "SCHL", "GNK", "SERV", "EE", "GPRE", "BWMN", "SLDP", "ACEL", "MRTN", "HELE", "CBL", "SBGI", "GCMG", "HNRG", "IOVA", "RDVT", "BCAX", "NUS", "IRMD", "BXC", "IBRX", "OXM", "IVR", "WSR", "NABL", "DJCO", "EGBN", "GRPN", "MPB", "OSPN", "VSTS", "CLB", "CCSI", "FSBC", "GDYN", "GOOD", "AMBP", "ARHS", "MCBS", "GSM", "TNGX", "ARCT", "FCBC", "OFIX", "MNRO", "CLMB", "CRNC", "CMRE", "TBPH", "HRTG", "SIBN", "GSBC", "FMNB", "KFRC", "SANA", "FOR", "KREF", "CASS", "WASH", "SMBC", "SMBK", "SENEA", "KROS", "SKYT", "FISI", "ALX", "KOP", "RUSHB", "AVO", "ETON", "NGVC", "NWPX", "BLZE", "ASIX", "SSTK", "UHT", "ORKA", "SPFI", "VIR", "GTN", "CWCO", "GIC", "ZVRA", "SHBI", "RDW", "FWRD", "DOMO", "PGEN", "MAZE", "RIGL", "EBS", "AEVA", "GRND", "RAPP", "FIP", "ALRS", "PLAY", "HZO", "SVV", "JBSS", "FSUN", "RGNX", "PRME", "NVGS", "PHAT", "BKKT", "TCBX", "WRLD", "AQST", "CTO", "VREX", "BHB", "RYAM", "AROW", "TROX", "PLPC", "NLOP", "ASPN", "HCKT", "LIND", "FPI", "GEVO", "FLGT", "GOSS", "NRIM", "NRDS", "SFIX", "GRDN", "NB", "CARE", "ABSI", "CYRX", "ANGO", "CODI", "NXDR", "AVBP", "CLNE", "CAL", "SITC", "XRX", "NFBK", "PGC", "IDR", "TIPT", "KOD", "HY", "PFIS", "KODK", "BMBL", "KALV", "LTBR", "MLR", "LXU", "PVLA", "CNDT", "THRY", "ABAT", "PSFE", "MITK", "PUMP", "AEBI", "SWBI", "BAND", "EBF", "REAX", "HIFS", "CTKB", "TK", "IBEX", "ACNB", "SEPN", "AVAH", "DIN", "FULC", "VOYG", "CMCO", "RES", "KOPN", "SVC", "RPAY", "CHCT", "CRVS", "FBIZ", "JELD", "ASC", "OEC", "CLFD", "VSTM", "SD", "BSRR", "PRTA", "SVRA", "EGY", "PACB", "CLBK", "KELYA", "YORW", "IBTA", "BYRN", "ITIC", "OLP", "WLFC", "BKV", "DC", "DDD", "IMXI", "BATRA", "VPG", "CYH", "COFS", "HBCP", "CRSR", "LAB", "CTOS", "WNC", "TLS", "TALK", "PTLO", "NAGE", "WEAV", "MAGN", "TWI", "UNTY", "ERAS", "NUTX", "KRUS", "HTLD", "CIVB", "BOW", "ULCC", "MAX", "BFLY", "MLAB", "HDSN", "RM", "BMRC", "ACCO", "BCAL", "SIGA", "JACK", "NFE", "SION", "GLRE", "PKE", "KRNY", "CBNK", "OIS", "MCS", "EOLS", "CTEV", "BFS", "CWBC", "CVLG", "MGTX", "SPIR", "HBT", "MTW", "RR", "MNPR", "MAMA", "TTAM", "BWB", "WTBA", "PSTL", "FRBA", "LXFR", "GBFH", "RBBN", "SFST", "MCFT", "GLUE", "TSSI", "FDMT", "MGPI", "SLDE", "RBB", "ARKO", "PUBM", "REPX", "PLSE", "CMPX", "BGS", "HNST", "SLDB", "MSBI", "SRTA", "FMAO", "SWIM", "VLGEA", "DGICA", "MTRX", "TITN", "MBI", "CENT", "PSNL", "EDIT", "AGL", "TRC", "BCML", "ZBIO", "MRVI", "NEXN", "INBX", "CMRC", "TCMD", "MVIS", "IHRT", "GNE", "CLDT", "AIP", "CLW", "RHLD", "WBTN", "ARDT", "BWFG", "KMTS", "TYRA", "MVBF", "BVS", "CBAN", "DCTH", "ALT", "REPL", "ORN", "ATLC", "CZNC", "LAND", "IPI", "ILPT", "WOOF", "USNA", "OBT", "CAPR", "SPOK", "CMTG", "CRCT", "NVEC", "GCO", "XPER", "TMCI", "ACIC", "KIDS", "NATH", "MOV", "RXST", "ANNX", "FNLC", "CGEM", "KRRO", "ALDX", "NEWT", "FLOC", "ORGO", "FSBW", "ZUMZ", "CBLL", "SLQT", "GRNT", "RRBI", "DSGR", "ADCT", "DNUT", "OOMA", "HVT", "BETR", "VNDA", "NCMI", "OPRX", "FRPH", "CERS", "BOC", "EGHT", "PDLB", "ZIP", "NECB", "FET", "JBIO", "UIS", "CZFS", "TE", "OMER", "RCKT", "OPFI", "NGS", "PKBK", "STRT", "BRBS", "SNWV", "PCB", "CRML", "PACK", "CDZI", "AVNW", "LFMD", "TSBK", "FSTR", "TH", "MBX", "RNGR", "NPCE", "SLP", "PLBC", "SB", "MEI", "FVR", "RMR", "AMCX", "LOCO", "ONIT", "VTEX", "LDI", "AURA", "IRWD", "MH", "ASLE", "HYLN", "NATR", "TBCH", "DRUG", "WSBF", "ACRE", "VUZI", "ATEX", "LMNR", "BZAI", "LILA", "RICK", "SATL", "RMNI", "NNOX", "PDYN", "JMSB", "BKTI", "QSI", "QTRX", "MASS", "ISTR", "INSE", "MCHB", "OSUR", "OM", "ABEO", "HSHP", "FEIM", "OPRT", "BH", "ARQ", "PBYI", "FRST", "CIA", "PAYS", "VMD", "GETY", "ALEC", "REFI", "VYGR", "CADL", "HUMA", "BSVN", "MPAA", "LOVE", "EVEX", "PLTK", "MITT", "CRMT", "ALMS", "LPRO", "TNXP", "XPOF", "FENC", "FTK", "LEGH", "FDBC", "III", "PCYO", "RCKY", "DMAC", "CATX", "JOUT", "IMMR", "AVIR", "DOUG", "TG", "CDXS", "JRVR", "FC", "ENTA", "KLC", "NGNE", "CTGO", "FBLA", "ASUR", "INR", "OMDA", "INGN", "INSG", "LRMR", "HRTX", "PKOH", "USAU", "FVCB", "BNTC", "OVLY", "CHMG", "SMC", "RLGT", "NWFL", "LCNB", "ATLO", "SKIN", "ALLO", "HCAT", "MEC", "LFCR", "SKYH", "WTI", "MYFW", "QUAD", "CFFI", "BRT", "FUNC", "MFIN", "HLLY", "KRT", "LVWR", "VEL", "LE", "NPB", "ONEW", "INBK", "VABK", "ALCO", "NKSH", "JAKK", "STXS", "WNEB", "USCB", "CHRS", "SEG", "STRZ", "EVCM", "OLPX", "BYND", "KINS", "RMAX", "PRTH", "SLS", "KGEI", "WEST", "JCAP", "CURI", "BPRN", "PINE", "TRAK", "ALMU", "BHR", "TBI", "FLXS", "KULR", "RGP", "ARAY", "TECX", "WEYS", "FRAF", "PESI", "LXEO", "MXCT", "LAW", "BELFA", "BOOM", "TRDA", "TVRD", "MG", "SSP", "LZM", "GCBC", "NRC", "PLX", "ELDN", "ELMD", "EGAN", "BBCP", "CMT", "TTGT", "RGCO", "OABI", "TTSH", "SEVN", "DSGN", "PANL", "ACRS", "DMRC", "MED", "RSVR", "NC", "CTRN", "EVI", "VOXR", "SAMG", "PEBK", "BNED", "ATNI", "PBFS", "FSP", "FHTX", "UTMD", "BCBP", "FCCO", "ALTI", "SNDA", "ATOM", "OPBK", "KRMD", "ULH", "ADV", "EVC", "PAL", "HAIN", "AVD", "ALTG", "KLTR", "BRCC", "NXDT", "NMAX", "EPM", "SMHI", "BIOA", "MDWD", "LWAY", "HPK", "CRDF", "FATE", "LAKE", "SGHT", "AMBQ", "MNTK", "NREF", "MPTI", "POWW", "TARA", "MRBK", "AIRS", "AVR", "MLP", "TCX", "FFAI", "GENC", "KRO", "FINW", "FXNC", "SGC", "DH", "CVRX", "CMDB", "JYNT", "AISP", "JILL", "ESOA", "AII", "ACR", "DBI", "EFSI", "SPWR", "SMID", "ESCA", "AOMR", "DCGO", "DSP", "AIRO", "RXT", "EHTH", "HWBK", "AEYE", "ANIK", "LNSR", "EML", "STRS", "FNKO", "RELL", "FRD", "FCAP", "SSTI", "MNSB", "FORR", "MDV", "BVFL", "OVBC", "RCMT", "NPWR", "CBFV", "MAPS", "HBB", "FOA", "SNFCA", "SUNS", "HFFG", "ACU", "FLWS", "RNAC", "EXFY", "NODK", "STIM", "ACTG", "AIRJ", "SMTI", "NKTX", "FF", "LFVN", "CZWI", "GWRS", "SRBK", "OFLX", "CLAR", "PMTS", "SBFG", "EBMT", "AOUT", "INNV", "BSET", "LAZR", "ASIC", "BALY", "BTMD", "LARK", "CXDO", "DERM", "ZVIA", "VIRC", "STRW", "BARK", "MYPS", "RMBI", "NRDY", "PDEX", "GAIA", "RCEL", "ACNT", "WHG", "NVCT", "GYRE", "AARD", "EPSN", "RVSB", "IKT", "AFCG", "TTEC", "FNWD", "BFIN", "CFBK", "TCI", "WALD", "HNVR", "GLSI", "KG", "ILLR", "PAMT", "CSPI", "CPSS", "RPT", "TKNO", "CARL", "LUCD", "LUNG", "ATYR", "TEAD", "SFBC", "PNBK", "AREN", "UNB", "SLSN", "TLSI", "SKYX", "HURA", "ECBK", "PNRG", "SEAT", "LFT", "FTLF", "SKIL", "CURV", "CBNA", "EP", "TZOO", "ACDC", "CLPR", "NL", "TUSK", "ISPR", "SVCO", "VHI", "SI", "COSO", "NEON", "COOK", "HQI", "PROP", "OPAL", "INMB", "SIEB", "MKTW", "SLND", "ACTU", "VALU", "NXXT", "ELA", "CIX", "BEEP", "MYO", "SAFX", "SBC", "RBKB", "ARL", "VRM", "AFRI", "TVGN", "VGAS", "ZSPC", "CMBT"],
    '4-200': ['360.AX','4DX.AX','A2M.AX','AAI.AX','AFI.AX','AGL.AX','AIA.AX','ALD.AX','ALK.AX','ALL.AX','ALQ.AX','ALX.AX','AMC.AX','AMP.AX','ANN.AX','ANZ.AX','APA.AX','APE.AX','ARB.AX','ARG.AX','ASB.AX','ASX.AX','AUB.AX','AZJ.AX','BEN.AX','BFL.AX','BGA.AX','BGL.AX','BHP.AX','BOQ.AX','BPT.AX','BRG.AX','BSL.AX','BWP.AX','BXB.AX','CAR.AX','CBA.AX','CDA.AX','CEN.AX','CGF.AX','CHC.AX','CIA.AX','CIP.AX','CLW.AX','CMM.AX','CNU.AX','COH.AX','COL.AX','CPU.AX','CQR.AX','CSC.AX','CSL.AX','CTD.AX','CWY.AX','CYL.AX','DBI.AX','DNL.AX','DOW.AX','DRO.AX','DRR.AX','DXS.AX','DYL.AX','EBO.AX','EDV.AX','EMR.AX','EOS.AX','EVN.AX','EVT.AX','FBU.AX','FLT.AX','FMG.AX','FPH.AX','FRW.AX','GDG.AX','GGP.AX','GMD.AX','GMG.AX','GNE.AX','GPT.AX','GQG.AX','HDN.AX','HUB.AX','HVN.AX','IAG.AX','IFT.AX','IGO.AX','ILU.AX','IMD.AX','JBH.AX','JHX.AX','L1G.AX','LLC.AX','LNW.AX','LOV.AX','LSF.AX','LTR.AX','LYC.AX','MCY.AX','MEZ.AX','MFF.AX','MFG.AX','MGR.AX','MIN.AX','MND.AX','MPL.AX','MQG.AX','MSB.AX','MTS.AX','MXT.AX','NAB.AX','NEM.AX','NHC.AX','NHF.AX','NIC.AX','NST.AX','NWH.AX','NWL.AX','NWS.AX','NXG.AX','NXT.AX','OBM.AX','ORA.AX','ORG.AX','ORI.AX','PDI.AX','PDN.AX','PLS.AX','PME.AX','PMV.AX','PNI.AX','PPT.AX','PRN.AX','PRU.AX','PXA.AX','QAN.AX','QBE.AX','RDX.AX','REA.AX','REG.AX','REH.AX','RGN.AX','RHC.AX','RIO.AX','RMD.AX','RMS.AX','RRL.AX','RSG.AX','RWC.AX','RYM.AX','S32.AX','SCG.AX','SDF.AX','SEK.AX','SFR.AX','SGH.AX','SGM.AX','SGP.AX','SHL.AX','SIG.AX','SMR.AX','SNZ.AX','SOL.AX','SPK.AX','STO.AX','SUL.AX','SUN.AX','TAH.AX','TCL.AX','TLC.AX','TLS.AX','TLX.AX','TNE.AX','TPG.AX','TUA.AX','TWE.AX','VAU.AX','VCX.AX','VEA.AX','VGN.AX','VNT.AX','WAF.AX','WAM.AX','WBC.AX','WDS.AX','WES.AX','WGX.AX','WHC.AX','WLE.AX','WOR.AX','WOW.AX','WTC.AX','XRO.AX','YAL.AX','ZIM.AX','ZIP.AX'],
    '5-ftse100': ['III.L','ABDN.L','ADM.L','AAF.L','ALW.L','AAL.L','ANTO.L','ABF.L','AZN.L','AUTO.L','AV.L','BAB.L','BA.L','BBY.L','BARC.L','BTRW.L','BP.L','BATS.L','BLND.L','BT-A.L','BNZL.L','BRBY.L','CNA.L','CCEP.L','CCH.L','CPG.L','CCC.L','CTEC.L','CRDA.L','DCC.L','DGE.L','DPLM.L','EZJ.L','EDV.L','EXPN.L','FCIT.L','FRES.L','GAW.L','GLEN.L','GSK.L','HLN.L','HLMA.L','HSX.L','HWDN.L','HSBA.L','ICG.L','IGG.L','IHG.L','IMI.L','IMB.L','INF.L','IAG.L','ITRK.L','INVP.L','ITH.L','JD.L','BGEO.L','KGF.L','LAND.L','LGEN.L','LLOY.L','LMP.L','LSEG.L','MNG.L','MKS.L','MRO.L','MTLN.L','NG.L','NWG.L','NXT.L','PSON.L','PSH.L','PCT.L','PRU.L','RKT.L','REL.L','RTO.L','RIO.L','RR.L','SGE.L','SBRY.L','SMT.L','SGRO.L','SVT.L','SHEL.L','SMIN.L','SN.L','SPX.L','SSE.L','STAN.L','SDLF.L','STJ.L','TSCO.L','BBOX.L','ULVR.L','UU.L','VOD.L','WEIR.L','WTB.L','WPP.L'],
    '5-nikkei225': ['8035.T','9202.T','9201.T','543A.T','7267.T','7202.T','7261.T','7211.T','7201.T','7270.T','7269.T','7203.T','7272.T','8304.T','8331.T','8354.T','8306.T','8411.T','8308.T','5831.T','8316.T','8309.T','7186.T','3407.T','4061.T','4901.T','4452.T','3405.T','4188.T','4183.T','4021.T','6988.T','4004.T','4063.T','4911.T','4005.T','4043.T','4042.T','4208.T','9433.T','9432.T','9434.T','9984.T','1721.T','1925.T','1808.T','1963.T','1812.T','1802.T','1928.T','1803.T','1801.T','6857.T','6770.T','7751.T','6902.T','6954.T','6504.T','6702.T','6501.T','6861.T','285A.T','6971.T','6920.T','6479.T','6503.T','6981.T','6701.T','6594.T','6645.T','6752.T','6723.T','7752.T','6963.T','7735.T','6724.T','6753.T','6758.T','6526.T','6976.T','6762.T','6506.T','6841.T','9502.T','9503.T','9501.T','1332.T','2802.T','2502.T','2914.T','2801.T','2503.T','2269.T','2282.T','2871.T','2002.T','2501.T','9532.T','9531.T','5201.T','5333.T','5214.T','5233.T','5301.T','5332.T','8750.T','8725.T','8630.T','8795.T','8766.T','9147.T','9064.T','6113.T','6367.T','6361.T','6305.T','7004.T','7013.T','5631.T','6473.T','6301.T','6326.T','7011.T','6471.T','6472.T','6103.T','6302.T','6273.T','9107.T','9104.T','9101.T','1605.T','5714.T','5803.T','5801.T','5711.T','5706.T','3436.T','5802.T','5713.T','8253.T','8697.T','8591.T','7832.T','7912.T','7911.T','7951.T','5020.T','5019.T','4503.T','4519.T','4568.T','4523.T','4151.T','4578.T','4506.T','4507.T','4502.T','6146.T','7741.T','4902.T','7731.T','7733.T','4543.T','3861.T','9022.T','9020.T','9008.T','9009.T','9007.T','9001.T','9005.T','9021.T','8802.T','8801.T','8830.T','8804.T','3289.T','8267.T','9983.T','3099.T','3086.T','8252.T','7453.T','9843.T','7532.T','3382.T','8233.T','3092.T','5108.T','5101.T','8601.T','8604.T','6532.T','4751.T','2432.T','4324.T','6178.T','9766.T','4689.T','4385.T','2413.T','3659.T','7974.T','4307.T','4661.T','4755.T','6098.T','9735.T','3697.T','9602.T','4704.T','7012.T','5411.T','5406.T','5401.T','3401.T','3402.T','8001.T','8002.T','8058.T','8031.T','2768.T','8053.T','8015.T'],
    '4-300': ['360.AX','4DX.AX','A2M.AX','AAI.AX','AFI.AX','AGL.AX','AIA.AX','ALD.AX','ALK.AX','ALL.AX','ALQ.AX','ALX.AX','AMC.AX','AMP.AX','ANN.AX','ANZ.AX','APA.AX','APE.AX','ARB.AX','ARG.AX','ASB.AX','ASX.AX','AUB.AX','AZJ.AX','BEN.AX','BFL.AX','BGA.AX','BGL.AX','BHP.AX','BOQ.AX','BPT.AX','BRG.AX','BSL.AX','BWP.AX','BXB.AX','CAR.AX','CBA.AX','CDA.AX','CEN.AX','CGF.AX','CHC.AX','CIA.AX','CIP.AX','CLW.AX','CMM.AX','CNU.AX','COH.AX','COL.AX','CPU.AX','CQR.AX','CSC.AX','CSL.AX','CTD.AX','CWY.AX','CYL.AX','DBI.AX','DNL.AX','DOW.AX','DRO.AX','DRR.AX','DXS.AX','DYL.AX','EBO.AX','EDV.AX','EMR.AX','EOS.AX','EVN.AX','EVT.AX','FBU.AX','FLT.AX','FMG.AX','FPH.AX','FRW.AX','GDG.AX','GGP.AX','GMD.AX','GMG.AX','GNE.AX','GPT.AX','GQG.AX','HDN.AX','HUB.AX','HVN.AX','IAG.AX','IFT.AX','IGO.AX','ILU.AX','IMD.AX','JBH.AX','JHX.AX','L1G.AX','LLC.AX','LNW.AX','LOV.AX','LSF.AX','LTR.AX','LYC.AX','MCY.AX','MEZ.AX','MFF.AX','MFG.AX','MGR.AX','MIN.AX','MND.AX','MPL.AX','MQG.AX','MSB.AX','MTS.AX','MXT.AX','NAB.AX','NEM.AX','NHC.AX','NHF.AX','NIC.AX','NST.AX','NWH.AX','NWL.AX','NWS.AX','NXG.AX','NXT.AX','OBM.AX','ORA.AX','ORG.AX','ORI.AX','PDI.AX','PDN.AX','PLS.AX','PME.AX','PMV.AX','PNI.AX','PPT.AX','PRN.AX','PRU.AX','PXA.AX','QAN.AX','QBE.AX','RDX.AX','REA.AX','REG.AX','REH.AX','RGN.AX','RHC.AX','RIO.AX','RMD.AX','RMS.AX','RRL.AX','RSG.AX','RWC.AX','RYM.AX','S32.AX','SCG.AX','SDF.AX','SEK.AX','SFR.AX','SGH.AX','SGM.AX','SGP.AX','SHL.AX','SIG.AX','SMR.AX','SNZ.AX','SOL.AX','SPK.AX','STO.AX','SUL.AX','SUN.AX','TAH.AX','TCL.AX','TLC.AX','TLS.AX','TLX.AX','TNE.AX','TPG.AX','TUA.AX','TWE.AX','VAU.AX','VCX.AX','VEA.AX','VGN.AX','VNT.AX','WAF.AX','WAM.AX','WBC.AX','WDS.AX','WES.AX','WGX.AX','WHC.AX','WLE.AX','WOR.AX','WOW.AX','WTC.AX','XRO.AX','YAL.AX','ZIM.AX','ZIP.AX','AAC.AX','AAJ.AX','AAP.AX','AAR.AX','AAU.AX','ABB.AX','ABY.AX','ACF.AX','ACL.AX','ACQ.AX','ACR.AX','ACS.AX','ACW.AX','ADH.AX','ADN.AX','ADO.AX','ADR.AX','ADS.AX','ADX.AX','AEF.AX','AEI.AX','AEL.AX','AER.AX','AEV.AX','AFG.AX','AFL.AX','AFP.AX','AGC.AX','AGD.AX','AGE.AX','AGI.AX','AGN.AX','AGR.AX','AGY.AX','AHF.AX','AHK.AX','AHL.AX','AHN.AX','AIM.AX','AIQ.AX','AIS.AX','AIV.AX','AIZ.AX','AJL.AX','AJX.AX','ALC.AX','ASL.AX','ATX.AX','AUG.AX','AVH.AX','AXP.AX','BAP.AX','BEL.AX','BKI.AX','BRN.AX','BRU.AX','BUX.AX','CCX.AX','CIN.AX','CMW.AX','CNI.AX','CRB.AX','CUV.AX','DMP.AX','DTL.AX','ELD.AX','EML.AX','GDF.AX','GNC.AX','GOZ.AX','GWA.AX','HMC.AX','IDX.AX','IMU.AX','IRE.AX','KGN.AX','KLS.AX','KMD.AX','LIC.AX','LKE.AX','MYR.AX','NAN.AX','NEC.AX','NUF.AX','NVX.AX','PAB.AX','PBH.AX','PNV.AX','SBM.AX','SCP.AX','SGR.AX','SMI.AX','SPN.AX','STX.AX','TYR.AX','URF.AX','VAS.AX','WEB.AX','WPR.AX'],
    '7-coinspot': []
}

def lambda_handler(event, context):
    """Coordinator Lambda that orchestrates worker Lambdas"""
    try:
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event
        
        option = body.get('option')
        sub_option = body.get('subOption') or body.get('sub_option')  # Support both formats
        user_id = body.get('userId') or body.get('user_id')  # Support both formats
        
        key = f"{option}-{sub_option}"
        
        if key not in WORKER_URLS:
            return {
                'statusCode': 400,
                'body': json.dumps({'success': False, 'error': f'Unknown screener: {key}'})
            }
        
        worker_urls = WORKER_URLS[key]
        stock_universe = STOCK_UNIVERSES.get(key, [])
        
        # Determine if workers use stock_batch or worker_id
        uses_worker_id = key in ['3-4', '3-5', '3-6']
        
        # For worker_id based screeners, get worker count
        if uses_worker_id:
            worker_counts = {'3-4': 150, '3-5': 100, '3-6': 200}
            worker_count = worker_counts.get(key, 0)
            if worker_count == 0:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'success': False, 'error': f'No worker count configured for screener: {key}'})
                }
        else:
            # Check if workers are configured for stock_batch based screeners
            if not worker_urls:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'success': False, 'error': f'No workers configured for screener: {key}'})
                }
        
        # Handle crypto orchestrator separately (single call, no workers)
        if key == '7-1':
            try:
                payload = json.dumps({'threshold': body.get('threshold', 0.25), 'enablePredictions': body.get('enablePredictions', True)}).encode('utf-8')
                req = urllib.request.Request(worker_urls[0], data=payload, headers={'Content-Type': 'application/json'})
                
                with urllib.request.urlopen(req, timeout=300) as response:
                    response_data = response.read()
                    data = json.loads(response_data)
                    
                    # Extract results from crypto orchestrator response
                    crypto_results = data if isinstance(data, list) else data.get('coins', data.get('results', []))
                    orchestrator_report = data.get('report', '') if isinstance(data, dict) else ''
                    print(f"🔍 Extracted crypto_results count: {len(crypto_results)}")
                    
                    # Save to user history if userId provided
                    if user_id and crypto_results:
                        # Use orchestrator's report if available, otherwise generate one
                        if orchestrator_report:
                            report = orchestrator_report
                        else:
                            report = f"""============================================================
🎯 CRYPTO SCREENER RESULTS (REAL-TIME DATA)
============================================================

Screening Universe: 548 Cryptocurrencies
Market Type: Crypto (Dynamic)
Universe Size: 548
Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🟢 TOP 10 BY SCORE:
"""
                        
                        if not orchestrator_report:
                            for i, coin in enumerate(crypto_results[:10], 1):
                                symbol = (coin.get('symbol', 'N/A') + '     ')[:5]
                                try:
                                    price_val = float(coin.get('price', 0))
                                except (ValueError, TypeError):
                                    price_val = 0.0
                                price = f"${price_val:.4f}"
                                price = (' ' * (12 - len(price))) + price
                                try:
                                    score = float(coin.get('score', 0))
                                except (ValueError, TypeError):
                                    score = 0.0
                                score_str = f"+{score:.1f}" if score >= 0 else f"{score:.1f}"
                                try:
                                    change = float(coin.get('change_24h', 0))
                                except (ValueError, TypeError):
                                    change = 0.0
                                change_str = f"+{change:.1f}%" if change >= 0 else f"{change:.1f}%"
                                try:
                                    vol_val = float(coin.get('volume_24h', 0))/1000000
                                except (ValueError, TypeError):
                                    vol_val = 0.0
                                vol = f"{vol_val:.1f}M"
                                report += f"{i:2d}. {symbol} {price} | Score: {score_str} | 24h: {change_str}, Vol: ${vol}\n"
                        
                            report += "\n🎯 TOP 3 DETAILED ANALYSIS:\n"
                            report += "================================================================\n"
                            for i, coin in enumerate(crypto_results[:3], 1):
                                try:
                                    score = float(coin.get('score', 0))
                                except (ValueError, TypeError):
                                    score = 0.0
                                score_str = f"+{score:.1f}" if score >= 0 else f"{score:.1f}"
                                try:
                                    price_val = float(coin.get('price',0))
                                except (ValueError, TypeError):
                                    price_val = 0.0
                                report += f"{i}. {coin.get('symbol','N/A')}: ${price_val:.4f} | {signal_label(coin.get('recommendation','HOLD'))} | Score: {score_str}\n"
                                try:
                                    ch24 = float(coin.get('change_24h',0))
                                except (ValueError, TypeError):
                                    ch24 = 0.0
                                try:
                                    ch7d = float(coin.get('change_7d',0))
                                except (ValueError, TypeError):
                                    ch7d = 0.0
                                report += f"   📈 24h Change: {ch24:.1f}% | 7d: {ch7d:.1f}%\n"
                                try:
                                    mcap = float(coin.get('market_cap',0))/1000000
                                except (ValueError, TypeError):
                                    mcap = 0.0
                                try:
                                    vol24 = float(coin.get('volume_24h',0))/1000000
                                except (ValueError, TypeError):
                                    vol24 = 0.0
                                report += f"   💰 Market Cap: ${mcap:.1f}M | Volume: ${vol24:.1f}M\n"
                                conf_val = coin.get('confidence',0)
                                if isinstance(conf_val, str):
                                    conf_str = conf_val
                                else:
                                    try:
                                        conf_str = f"{float(conf_val):.0f}%"
                                    except (ValueError, TypeError):
                                        conf_str = "N/A"
                                report += f"   🎯 Prediction: {coin.get('prediction','N/A')} | Confidence: {conf_str}\n\n"
                        
                            def safe_float(val, default=0.0):
                                try:
                                    return float(val)
                                except (ValueError, TypeError):
                                    return default
                        
                            positive = sum(1 for c in crypto_results if safe_float(c.get('score', 0)) > 0)
                            negative = sum(1 for c in crypto_results if safe_float(c.get('score', 0)) < 0)
                            avg_score = sum(safe_float(c.get('score', 0)) for c in crypto_results) / len(crypto_results) if crypto_results else 0
                        
                            report += f"\n📊 ANALYSIS SUMMARY:\n"
                            report += f"• Total coins analyzed: {len(crypto_results)}\n"
                            report += f"• Coins with positive scores: {positive}\n"
                            report += f"• Coins with negative scores: {negative}\n"
                            report += f"• Average score: {avg_score:.1f}\n"
                            report += f"\n✅ Real-time crypto screening complete!"
                        
                        def safe_float(val, default=0.0):
                            try:
                                return float(val)
                            except (ValueError, TypeError):
                                return default
                        
                        # Generate CSV matching WebUI format
                        csv_lines = ['Rank,Symbol,Price,Score,Signal,Timeframe,Confidence,RSI,24h_Change_%,7d_Change_%,30d_Change_%,Volume_Ratio,Model_Probability_%,MACD_Signal,BB_Signal,Momentum_Signal,Lower_Level,Upper_Level,Support,Resistance,ATR,Stoch_K,MACD_Trend,Top10_Status']
                        for i, c in enumerate(crypto_results, 1):
                            rec = signal_label(c.get('recommendation','HOLD'))
                            tf = horizon_label(c.get('timeframe','N/A'))
                            conf = c.get('confidence','LOW')
                            macd_sig = c.get('macd_signal','No data').replace('"', '""')
                            bb_sig = c.get('bb_signal','NEUTRAL').replace('"', '""')
                            mom_sig = c.get('momentum_signal','NEUTRAL').replace('"', '""')
                            macd_trend = c.get('macd_trend','NEUTRAL')
                            pred_status = c.get('prediction_status','')
                            csv_lines.append(f'{i},{c.get("symbol","N/A")},{safe_float(c.get("price",0)):.8f},{safe_float(c.get("score",0))},{rec},{tf},{conf},{safe_float(c.get("rsi",50)):.1f},{safe_float(c.get("change_24h",0)):.2f},{safe_float(c.get("change_7d",0)):.2f},{safe_float(c.get("change_30d",0)):.2f},{safe_float(c.get("volume_ratio",1)):.2f},{safe_float(c.get("profit_probability",50)):.0f},"{macd_sig}","{bb_sig}","{mom_sig}",{safe_float(c.get("stop_loss",0)):.8f},{safe_float(c.get("take_profit",0)):.8f},{safe_float(c.get("support",0)):.8f},{safe_float(c.get("resistance",0)):.8f},{safe_float(c.get("atr",0)):.8f},{safe_float(c.get("stoch_k",50)):.1f},{macd_trend},{pred_status}')
                        csv_data = '\n'.join(csv_lines)
                        
                        save_payload = json.dumps({
                            'action': 'save_analysis',
                            'userId': user_id,
                            'symbol': 'Analysis 7-1',
                            'companyName': 'Crypto Universe Screener',
                            'report': report,
                            'csvData': csv_data,
                            'isRead': False
                        }).encode('utf-8')
                        
                        save_req = urllib.request.Request(
                            'https://nwdjnlcbtj34ywy6sgawmwhcx40ologt.lambda-url.us-east-1.on.aws/',
                            data=save_payload,
                            headers={'Content-Type': 'application/json'}
                        )
                        
                        with urllib.request.urlopen(save_req, timeout=10) as save_response:
                            print(f"Saved crypto results to history for user {user_id}")
                    
                    return {
                        'statusCode': 200,
                        'body': json.dumps({
                            'success': True,
                            'results': crypto_results,
                            'stocks_analyzed': len(crypto_results),
                            'universe_size': 548
                        })
                    }
            except Exception as e:
                print(f"❌ Crypto orchestrator error: {e}")
                return {'statusCode': 500, 'body': json.dumps({'success': False, 'error': str(e)})}
        
        batch_size = 10
        results = []
        
        def call_worker(worker_id, url, stock_batch=None):
            """Call a single worker Lambda"""
            try:
                if uses_worker_id:
                    payload = json.dumps({'worker_id': worker_id, 'batch_size': batch_size}).encode('utf-8')
                else:
                    payload = json.dumps({'stock_batch': stock_batch, 'worker_id': worker_id}).encode('utf-8')
                
                req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=300) as response:
                    data = json.loads(response.read())
                    return data.get('results', [])
            except Exception as e:
                print(f"Worker {worker_id} failed: {e}")
                return []
        
        # Call workers in parallel
        if uses_worker_id:
            # For worker_id based screeners, invoke workers by function name
            import boto3
            lambda_client = boto3.client('lambda')
            function_prefix = f"stockiq-option-{option}-{sub_option}-worker-"
            max_workers = min(worker_count, 50)
            
            def call_worker_by_id(worker_id):
                try:
                    function_name = f"{function_prefix}{worker_id}"
                    # Calculate stock batch for this worker
                    per_worker = max(batch_size, -(-len(stock_universe) // worker_count)) if stock_universe else batch_size
                    start_idx = (worker_id - 1) * per_worker
                    end_idx = start_idx + per_worker
                    worker_stock_batch = stock_universe[start_idx:end_idx] if stock_universe else []
                    if stock_universe and not worker_stock_batch:
                        return []  # nothing left for this worker: do not call it (it would use its built-in list)
                    payload = json.dumps({'worker_id': worker_id, 'batch_size': batch_size, 'stock_batch': worker_stock_batch}).encode('utf-8')
                    
                    response = lambda_client.invoke(
                        FunctionName=function_name,
                        InvocationType='RequestResponse',
                        Payload=payload
                    )
                    
                    if response['StatusCode'] == 200:
                        response_payload = json.loads(response['Payload'].read())
                        body = json.loads(response_payload.get('body', '{}')) if isinstance(response_payload.get('body'), str) else response_payload
                        return body.get('results', [])
                    return []
                except Exception as e:
                    print(f"Worker {worker_id} failed: {e}")
                    return []
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(call_worker_by_id, i) for i in range(1, worker_count + 1)]
                for future in as_completed(futures):
                    results.extend(future.result())
        else:
            # For stock_batch based screeners, call via URLs
            with ThreadPoolExecutor(max_workers=len(worker_urls)) as executor:
                futures = []
                for i, url in enumerate(worker_urls):
                    # Spread the list over the workers: 10 each, a few more only when the list is longer than
                    # workers x 10. Workers with nothing to do are not called (an empty batch must never be sent:
                    # some workers fall back to a list built into their own code).
                    per_worker = max(batch_size, -(-len(stock_universe) // len(worker_urls)))
                    start_idx = i * per_worker
                    stock_batch = stock_universe[start_idx:start_idx + per_worker]
                    if stock_batch:
                        futures.append(executor.submit(call_worker, i + 1, url, stock_batch))
                
                for future in as_completed(futures):
                    results.extend(future.result())
        
        # A few lists contain the same symbol twice; keep one result per symbol
        seen_symbols = set()
        unique_results = []
        for r in results:
            sym = r.get('symbol')
            if sym in seen_symbols:
                continue
            seen_symbols.add(sym)
            unique_results.append(r)
        results = unique_results

        # Sort by score
        results.sort(key=lambda x: x.get('total_score', 0), reverse=True)
        
        # Save to user's history if userId provided
        if user_id:
            try:
                screener_names = {
                    '3-100': 'S&P 100 Basic Screener',
                    '3-2': 'S&P 400+600 (Mid+SmallCap)',
                    '3-3': 'S&P 500 Complete Screener',
                    '3-4': 'S&P Composite 1500',
                    '3-5': 'Russell 1000 Large-Cap Screener',
                    '3-6': 'Russell 2000 Small-Cap Screener',
                    '3-7': 'NASDAQ 100 Tech Screener',
                    '3-8': 'Dow Jones 30 Blue Chip Screener',
                    '4-50': 'ASX 50 Screener',
                    '4-100': 'ASX 100 Screener',
                    '4-200': 'ASX 200 Screener',
                    '4-300': 'ASX 300 Screener',
                    '5-ftse100': 'UK FTSE 100 Screener',
                    '5-nikkei225': 'Japan Nikkei 225 Screener'
                }
                
                # Format report exactly like web UI
                titles = {'3-100': 'S&P 100 (OEX)', '3-2': 'S&P 400+600 (MID+SMALLCAP)', '3-3': 'S&P 500 COMPLETE', '3-4': 'S&P COMPOSITE 1500', '3-5': 'RUSSELL 1000 LARGE-CAP', '3-6': 'RUSSELL 2000 SMALL-CAP', '3-7': 'NASDAQ 100 TECH', '3-8': 'DOW JONES 30 BLUE CHIP', '4-50': 'ASX 50', '4-100': 'ASX 100', '4-200': 'ASX 200', '4-300': 'ASX 300', '5-ftse100': 'UK FTSE 100', '5-nikkei225': 'JAPAN NIKKEI 225'}
                title = titles.get(key, key)
                
                # Get universe size (for worker_id based screeners, use worker count * batch size)
                universe_sizes = {'3-100': 101, '3-2': 995, '3-3': 502, '3-4': 1497, '3-5': 877, '3-6': 1829, '3-7': 101, '3-8': 30, '4-50': 49, '4-100': 99, '4-200': 195, '4-300': 294, '5-ftse100': 100, '5-nikkei225': 225}
                universe_size = universe_sizes.get(key, len(stock_universe))
                
                report = "============================================================\n"
                report += f"🎯 {title} STOCK SCREENER RESULTS (REAL-TIME DATA)\n"
                report += "============================================================\n\n"
                report += f"Screening Universe: {universe_size} {title} stocks\n"
                report += f"Market Type: {title} Stocks (Dynamic)\n"
                report += f"Universe Size: {universe_size}\n"
                report += f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                report += "🟢 TOP 10 BY SCORE:\n"

                for i, stock in enumerate(results[:10], 1):
                    symbol = (stock.get('symbol', 'N/A') + '     ')[:5]
                    price = f"${stock.get('price', 0):.2f}"
                    price = (' ' * (8 - len(price))) + price
                    score = stock.get('total_score', 0)
                    score_str = f"+{score:.1f}" if score >= 0 else f"{score:.1f}"
                    rsi = f"{stock.get('rsi', 0):.1f}"
                    rsi = (' ' * (5 - len(rsi))) + rsi
                    ytd = stock.get('ytd_change', 0)
                    ytd_str = f"+{ytd:.1f}%" if ytd >= 0 else f"{ytd:.1f}%"
                    vol = f"{stock.get('volume_ratio', 1):.1f}x"
                    report += f"{i:2d}. {symbol} {price} | Score: {score_str} | RSI: {rsi} | YTD: {ytd_str}, Vol: {vol}\n"
                
                # Add detailed analysis for top 3
                report += "\n🎯 TOP 3 DETAILED ANALYSIS:\n"
                report += "================================================================\n"
                for i, stock in enumerate(results[:3], 1):
                    score = stock.get('total_score', 0)
                    score_str = f"+{score:.1f}" if score >= 0 else f"{score:.1f}"
                    report += f"{i}. {stock.get('symbol','N/A')}: ${stock.get('price',0):.2f} | {signal_label(stock.get('recommendation','HOLD'))} | Score: {score_str}\n"
                    if stock.get('score_breakdown'):
                        report += "   📊 Score Breakdown:\n"
                        for breakdown in stock['score_breakdown']:
                            report += f"      {breakdown}\n"
                    report += f"   📈 Technical: RSI {stock.get('rsi',50):.1f} | MACD {stock.get('macd_signal','NEUTRAL')}\n"
                    report += f"   💰 Levels: Support ${stock.get('support',0):.2f} | Resistance ${stock.get('resistance',0):.2f}\n"
                    report += f"   📏 Reference levels: Lower ${stock.get('stop_loss',0):.2f} | Upper ${stock.get('take_profit',0):.2f}\n"
                    report += f"   📊 Horizon: {horizon_label(stock.get('strategy_type','N/A'))} | Confidence: {stock.get('confidence',0):.0f}%\n\n"
                
                # Add summary
                positive = sum(1 for s in results if s.get('total_score', 0) > 0)
                negative = sum(1 for s in results if s.get('total_score', 0) < 0)
                avg_score = sum(s.get('total_score', 0) for s in results) / len(results) if results else 0
                success_rate = (len(results) / universe_size * 100) if universe_size > 0 else 0
                report += f"\n📊 ANALYSIS SUMMARY:\n"
                report += f"• Total stocks analyzed: {len(results)}\n"
                report += f"• Stocks with positive scores: {positive}\n"
                report += f"• Stocks with negative scores: {negative}\n"
                report += f"• Average score: {avg_score:.1f}\n"
                report += f"• Success rate: {success_rate:.1f}%\n"
                report += f"\n✅ Real-time {title} stock screening complete!"
                
                # Generate CSV exactly like web UI
                csv_lines = ['Rank,Symbol,Price,Score,Signal,Support,Resistance,Lower_Level,Upper_Level,Model_Probability_%,Horizon,Horizon_Days,Timeframe,Confidence_%,24h_Change_%,5d_Change_%,7d_Change_%,10d_Change_%,30d_Change_%,90d_Change_%,200d_Change_%,YTD_Change_%,RSI,MACD_Signal,BB_Signal,Momentum_Signal,Volume_Ratio,Stoch_K,ATR,Price_vs_MA20_%,Price_vs_MA50_%,Price_vs_MA200_%,Distance_52W_High_%,Distance_From_Low_%,52W_High,52W_Low,Market_Regime,SPY_20d_Change_%,Score_Breakdown']
                # PE_Ratio, Market_Cap, Beta, Dividend_Yield_%, Sector and Earnings_Risk are not exported: the workers do not
                # fetch them (they return fixed estimates). Field names below are the ones workers actually return.
                for i, s in enumerate(results, 1):
                    breakdown = ' | '.join(s.get('score_breakdown', [])) if s.get('score_breakdown') else ''
                    breakdown_escaped = breakdown.replace('"', '""')
                    rec = signal_label(s.get('recommendation','HOLD'))
                    strat = horizon_label(s.get('strategy_type','N/A')).replace('"', '""')
                    tf = horizon_label(s.get('timeframe','N/A')).replace('"', '""')
                    macd = s.get('macd_signal','NEUTRAL').replace('"', '""')
                    bb = s.get('bb_signal','NEUTRAL').replace('"', '""')
                    mom = s.get('momentum_signal','NEUTRAL').replace('"', '""')
                    mcap = str(s.get('market_cap','N/A')).replace('"', '""')
                    regime = s.get('market_regime','NEUTRAL').replace('"', '""')
                    sector = s.get('sector','OTHER').replace('"', '""')
                    risk = s.get('earnings_risk','LOW').replace('"', '""')
                    csv_lines.append(f'{i},{s.get("symbol","")},{s.get("price",0):.2f},{s.get("total_score",0)},"{rec}",{s.get("support",0):.2f},{s.get("resistance",0):.2f},{s.get("stop_loss",0):.2f},{s.get("take_profit",0):.2f},{s.get("profit_probability",50):.0f},"{strat}",{s.get("hold_days","N/A")},"{tf}",{s.get("confidence",50):.0f},{s.get("change_24h",0):.2f},{s.get("change_5d",0):.2f},{s.get("change_7d",0):.2f},{s.get("change_10d",0):.2f},{s.get("change_30d",0):.2f},{s.get("change_90d",0):.2f},{s.get("change_200d",0):.2f},{s.get("ytd_change",0):.2f},{s.get("rsi",50):.1f},"{macd}","{bb}","{mom}",{s.get("volume_ratio",1):.2f},{s.get("stoch_k",50):.1f},{s.get("atr",0):.2f},{s.get("price_vs_ma20",0):.2f},{s.get("price_vs_ma50",0):.2f},{s.get("price_vs_ma200",0):.2f},{s.get("distance_from_52w_high",0):.2f},{s.get("distance_from_52w_low", s.get("distance_from_low",0)):.2f},{s.get("52w_high", s.get("high_52w",0)):.2f},{s.get("52w_low", s.get("low_52w",0)):.2f},"{regime}",{s.get("spy_change_20d",0):.1f},"{breakdown_escaped}"')
                csv_data = '\n'.join(csv_lines)
                
                save_payload = json.dumps({
                    'action': 'save_analysis',
                    'userId': user_id,
                    'symbol': f'Analysis {key}',
                    'companyName': screener_names.get(key, f'Screener {key}'),
                    'report': report,
                    'csvData': csv_data,
                    'isRead': False
                }).encode('utf-8')
                
                save_req = urllib.request.Request(
                    'https://nwdjnlcbtj34ywy6sgawmwhcx40ologt.lambda-url.us-east-1.on.aws/',
                    data=save_payload,
                    headers={'Content-Type': 'application/json'}
                )
                
                with urllib.request.urlopen(save_req, timeout=10) as save_response:
                    print(f"Saved {key} to history for user {user_id}")
            except Exception as save_error:
                print(f"Failed to save to history: {save_error}")
        
        # Get universe size for response
        universe_sizes = {'3-100': 101, '3-2': 995, '3-3': 502, '3-4': 1497, '3-5': 877, '3-6': 1829, '3-7': 101, '3-8': 30, '4-50': 49, '4-100': 99, '4-200': 195, '4-300': 294, '5-ftse100': 100, '5-nikkei225': 225}
        response_universe_size = universe_sizes.get(key, len(stock_universe))
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'results': results,
                'stocks_analyzed': len(results),
                'universe_size': response_universe_size
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'success': False, 'error': str(e)})
        }
