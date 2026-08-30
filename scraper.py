import asyncio
import os
import hashlib
from crawl4ai import AsyncWebCrawler

async def run_climate_scraper():
    
    os.makedirs("data/raw", exist_ok=True)
    
    urls = [
        "https://www.ipcc.ch/report/ar6/syr/summary-for-policymakers/",
        "https://www.ipcc.ch/report/ar6/wg3/chapter/chapter-6/",
        "https://www.ipcc.ch/report/ar6/wg3/chapter/chapter-13/",
        "https://unfccc.int/fund-for-responding-to-loss-and-damage",
        "https://unfccc.int/cop29",
        "https://www.unfccc.int/zh/node/637774",
        "https://unfccc.int/cop28/outcomes",
        "https://www.irena.org/Publications/2026/May/Transitioning-away-from-fossil-fuels",
        "https://www.carbonbrief.org/debriefed-1-may-2026-countries-chart-path-away-from-fossil-fuels-chinas-clean-tech-surge-global-forest-loss-slows",
        "https://www.fossilfueltreaty.org/conference",
        "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_629",
        "https://www.iea.org/reports/oil-market-report-august-2026",
        "https://www.amnesty.org/en/latest/campaigns/2026/04/fossil-fuel-treaty/",
        "https://enb.iisd.org/transition-away-fossil-fuels-1-summary",
        "https://unfccc.int/topics/introduction-to-climate-finance",
        "https://www.iso.org/climate-change/climate-finance",
        "https://www.econjournals.com/index.php/ijeep/article/view/19799",
        "https://glcf.climatepolicyinitiative.org/",
        "https://climatefundsupdate.org/about-climate-finance/global-climate-finance-architecture/",
        "https://www.lse.ac.uk/granthaminstitute/explainers/what-is-the-just-transition-and-what-does-it-mean-for-climate-action/",
        "https://commission.europa.eu/topics/regional-and-urban-policy/just-transition-mechanism_en",
        "https://www.ilo.org/topics-and-sectors/just-transition-towards-environmentally-sustainable-economies-and-societies",
        "https://www.unepfi.org/social-issues/just-transition/",
        "https://energy.ec.europa.eu/strategy/energy-union/national-energy-and-climate-plans_en",
        "https://www.undp.org/egypt/projects/egypts-national-adaptation-plan-nap",
        "https://www.un.org/en/climatechange/all-about-ndcs",
        "https://climate-laws.org/document/egypt-national-climate-change-strategy-nccs-2050_d3b1",
        "https://www.thelancet.com/journals/lanplh/article/PIIS2542-5196(24)00303-6/fulltext",
        "https://www.allianz.com/en/economic_research/insights/publications/specials_fmo/2024_01_11-Climate-Change-Trade-Offs.html",
        "https://www.sciencedirect.com/science/article/abs/pii/S0959652620328584",
        "https://www.enel.com/learning-hub/renewables",
        "https://extension.psu.edu/what-is-renewable-energy",
        "https://www.enel.com/learning-hub/energy-transition",
        "https://www.energy-transitions.org/",
        "https://totalenergies.com/energy-transition",
        "https://about.bnef.com/insights/finance/energy-transition-investment-trends/",
        "https://www.irena.org/Energy-Transition/Outlook",
        "https://commission.europa.eu/topics/energy/energy-and-green-deal_en",
        "https://www.climate.gov/ghg/what-are-greenhouse-gases-and-why-do-they-matter",
        "https://climatetrace.org/news/climate-trace-releases-january-2026-emissions-data",
        "https://unu.edu/ehs/article/5-things-watch-climate-and-environment-2026",
        "https://terrapass.com/blog/climate-change-battle-causes-effects-and-solutions/",
        "https://unfccc.int/process-and-meetings/the-paris-agreement",
        "https://unfccc.int/news/paris-agreement-implementation-and-compliance-committee-2026-milestones",
        "https://www.wri.org/insights/paris-agreement-next-decade",
        "https://eelp.law.harvard.edu/tracker/paris-climate-agreement/",
        "https://treaties.un.org/pages/ViewDetails.aspx?chapter=27&clang=_en&mtdsg_no=XXVII-7-d&src=treaty",
        "https://www.dw.com/en/at-a-crossroads-fossil-fuel-powered-investments-or-renewables-profit/a-75243684",
        "https://www.sciencedirect.com/science/article/pii/S0973082625001036",
        "https://twn.my/title/climate/climate11.htm",
        "https://econ.gatech.edu/projects/are-fossil-fuel-resources-important-economic-development",
        "https://www.wri.org/insights/just-transition-developing-countries-shift-oil-gas",
        "https://www.arcticwwf.org/the-circle/stories/what-will-it-take-to-phase-out-fossil-fuels/",
        "https://www.sei.org/publications/development-transitions-fossil-fuel-producing-countries/",
        "https://unctad.org/news/least-developed-countries-cannot-afford-strand-their-assets-given-their-development-challenges",
        "https://www.climatechangenews.com/2026/04/22/to-phase-out-fossil-fuels-developing-countries-need-exit-route-from-debt-trap/",
        "https://www.boreal-is.com/blog/oil-and-gas-stakeholders/",
        "https://influencemap.org/finance-map",
        "https://cordis.europa.eu/project/id/826051",
        "https://www.mdpi.com/2071-1050/17/24/11146",
        "https://plana.earth/academy/the-stakeholders-of-climate-change",
        "https://www.theguardian.com/environment/2026/mar/26/fossil-fuel-companies-accept-climate-crisis-just-not-their-role-in-it",
        "https://people.climate.columbia.edu/projects/view/830",
        "https://www.sciencedirect.com/science/article/pii/S1364032125000322",
        "https://www.oxfam.org/en/press-releases/fossil-fuel-companies-projected-earn-almost-3000-second-2026-while-families-struggle",
        "https://commonhome.georgetown.edu/topics/climateenergy/defense-denial-and-disinformation-uncovering-the-oil-industrys-early-knowledge-of-climate-change/",
        "https://www.nature.com/articles/s41558-023-01734-0",
        "https://www.cell.com/one-earth/fulltext/S2590-3322(23)00198-7",
        "https://news.harvard.edu/gazette/story/2021/09/oil-companies-discourage-climate-action-study-says/",
        "https://www.nature.com/articles/d41586-023-01599-5",
        "https://balkangreenenergynews.com/renewables-are-several-times-more-profitable-than-fossil-fuels/",
        "https://www.iea.org/reports/the-oil-and-gas-industry-in-net-zero-transitions/executive-summary",
        "https://vasro.de/en/energy-market-equity-reports-fossil-fuels-vs-renewables/",
        "https://www.sciencedirect.com/science/article/pii/S2214629625003020",
        "https://www.un.org/en/climatechange/raising-ambition/renewable-energy",
        "https://met.com/en/mind-the-fyouture/mindthefyouture/can-renewable-energy-replace-fossil-fuels/",
        "https://iee.psu.edu/news/blog/transitioning-renewable-energy-challenges-and-opportunities",
        "https://www.robeco.com/en-int/glossary/sustainable-investing/fossil-fuel-alternatives",
        "https://www.sciencedirect.com/science/article/pii/S266695522300014X",
        "https://www.britannica.com/procon/alternative-energy-debate",
        "https://la-solargroup.com/are-there-ways-to-let-solar-energy-replace-fossil-fuels/",
        "https://www.intechopen.com/chapters/1214871",
        "https://knowhow.distrelec.com/sustainability/integrating-renewable-energy-systems-into-building-design/",
        "https://www.harperlatterarchitects.co.uk/post/renewable-energy-integration",
        "https://www.archdaily.com/tag/renewable-energy",
        "https://www.frld.org/",
        "https://www.undp.org/belarus/stories/loss-and-damage-fund-developing-countries",
        "https://www.sciencedirect.com/science/article/pii/S030142152600234X",
        "https://www.worldbank.org/en/programs/funding-for-loss-and-damage",
        "https://www.imf.org/en/topics/climate-change/energy-subsidies",
        "https://www.oecd.org/en/about/news/announcements/2025/12/government-support-for-fossil-fuels-remains-high-despite-a-10-decline.html",
        "https://gijn.org/resource/guide-investigating-fossil-fuels-guide-government-regulations-policies/",
        "https://climateactiontracker.org/blog/fossil-fuel-phase-out-how-are-governments-doing/",
        "https://www.gov.uk/government/publications/uk-fossil-fuel-incentives-and-subsidies-inventory/uk-fossil-fuel-incentives-and-subsidies-inventory",
        "https://www.sciencedirect.com/science/article/pii/S2214629626001738",
        "https://www.cesr.org/no-transition-without-workers/",
        "https://www.tandfonline.com/doi/full/10.1080/14693062.2025.2460665",
        "https://communities.springernature.com/posts/from-dirty-to-green-to-fossil-fuel-to-all-rethinking-who-gets-left-behind-in-the-energy-transition",
        "https://www.iea.org/reports/world-energy-employment-2023/executive-summary",
        "https://www.facebook.com/350.org/posts/workers-built-this-world-fossil-fuel-ceos-are-making-you-pay-for-it-to-every-wor/1428426132661379/",
        "https://onlinelibrary.wiley.com/doi/full/10.1111/anti.70032",
        "https://www.investopedia.com/investing/oil-gas-industry-overview/",
        "https://guides.loc.gov/oil-and-gas-industry",
        "https://www.fortunebusinessinsights.com/oil-and-gas-market-111534",
        "https://www.renewable-energy-industry.com/",
        "https://www.fortunebusinessinsights.com/renewable-energy-market-105511",
        "https://www.iea.org/energy-system/renewables-and-low-emissions-fuels",
        "https://umbrex.com/resources/how-industries-work/energy-natural-resources/how-the-renewable-energy-industry-works/",
        "https://www.climate-kic.org/",
        "https://www.ecologic.eu/20347",
        "https://www.greenclimate.fund/node/73640",
        "https://www.nature.com/articles/s41597-025-05308-x"
    ]
    
    print("Starting the AI Crawler...")
    
    async with AsyncWebCrawler(verbose=True) as crawler:
        for index, url in enumerate(urls, 1):
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            file_path = f"data/raw/doc_{url_hash}.md"
            
            if os.path.exists(file_path):
                print(f"[{index}/{len(urls)}] Already scraped, skipping: {url}")
                continue
            
            print(f"[{index}/{len(urls)}] Scraping: {url}")
            result = await crawler.arun(url=url)
            
            if result.success:
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(f"<!-- Source: {url} -->\n\n")
                    
                    # Safe extraction of markdown whether it's a string or an object
                    md_content = result.markdown
                    if hasattr(md_content, "raw_markdown"):
                        md_content = md_content.raw_markdown
                        
                    file.write(md_content)
                print(f" Saved clean text to {file_path}")
            else:
                print(f" Failed: {result.error_message}")
            
            await asyncio.sleep(3)
            
    print("\nDone! All documents safely saved without overwriting.")

if __name__ == "__main__":
    asyncio.run(run_climate_scraper())