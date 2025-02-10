# Android fragmentation and kernels
One of the most prominent aspects of Android devices is their diversity. Due to the open source nature of the project, many device
vendors use Android for their products. Different device manufacturers modify the base version of the OS, maintained by Google, for their unique enhancements. These independent, uncoordinated changes across vendors lead to fragmentation. Previous research has shown that this fragmentation can serve as a guide in vulnerability search, in other words, custom vendor code, if not reviewed/scrutinized enough, tends to introduce security risks. This work is a primer for securiy research about Android kernel fragmentation. This repo contains scripts for kernel analysis automation in order to quantify/outline extent of fragmentation, and in some useful information for work in this direction in general.

In short, the scripts collect 2 types of statistics: GKI modifications and source code modifications. In the first part, the kernels are pulled from a repository, analyzed in comparison to their GKI counterpart, and this information is dumped to a Google table.
In the second part, the script aggregates diff between vendor source code and AOSP kernel source code. The user needs to provide codebases for comparison, and in the end they get a digest on source code modifications.

# Setting up the environment

In order to get all the needed packages to run the scripts, create a virtual environment from the provided _requirements.txt_.
For environment `venv`:
```
virtualenv venv
source venv/bin/activate 
pip install -r requirements.txt
```

Make sure to export the current working directory with all the scripts: 
```
export KERNELS_ROOT_DIR=/path/to/curr/working/dir
``` 

One of the scripts also expects [vmlinux-to-elf](https://github.com/marin-m/vmlinux-to-elf) to be available as a command system-wide. Clone the repo and add it to PATH. 

# Analyze boot.img
## 1. Get a set of kernels
The kernels are taken from https://dumps.tadiphone.dev/. The script **pull_kernels.py** pulls boot.img of every model from target vendors. To specify these vendors, adjust *oem_list* variable. Make sure the names match those in the tadiphone repo. *baseline* variable specifies lowest acceptable kernel version (5.10.0 by default). 
pull_kernels.py will create a folder per vendor in the current working directory, containing folders per each model. 
On top of pulling a boot.img, pull_kernels.py script will also perform a search
for the corresponding GKI kernel. Kernel versioning information typically has the following format:
```
5.10.198-android12-9-00085-g226a9632f13d-ab11136126
```
where 5.10.198 is a base Linux kernel version, g226a9632f13d is the commit hash that uniquely identifies the specific source code revision, and ab11136126 is a specific Android build identifier.

Thus, if the vendors do not modify or conceal information about the exact kernel version, one can go to AOSP repository and
refer to the specific commit, or use the build number to find the corresponding GKI on the Android CI website. 
In case this information does not point to any valid commit/build in AOSP, the script performs a best-effort search based on the kernel
version. For example, if the claimed version is 5.10.198, the script will search the Android CI for a build with this version. 
One caveat would be the fact that there may be multiple builds for the 5.10.198, with silght differences between each other.
Thus, not knowing which patch to pick exactly, the safest assumption was to pick the first build of the 5.10.198 version. 
After the boot.img pull and corresponding GKI search, in case of no errors, per-model folders should contain:
 - orig-boot.elf
 - orig-boot.img
 - boot.img (or Image)
 - corresp-boot-oldest.elf

## 2. Dump stat on symbols and configs
The **dump_to_sheets.py** script expects a folder with extracted kernels (as arranged in the previous step).
Thus, the folder structure should look something like this (given that "samsung" and "redmi" kernels were pulled from the repository):

``` 
├── diffconfig
├── dump_to_sheets.py
├── pull_kernels.py
├── gki_scrape.py
├── syms_helpers.py
├── model_info_vpn.py
├── extract-ikconfig
├── README.md
├── samsung/
├── redmi/
├── ...
└── requirements.txt
```

This code is designed to aggregate information about kernels into Google spreadsheets. It uses Python module gspread, which requires a setup of a Google service account for automatic spreadsheet access. 
Refer to this [support page](https://support.google.com/a/answer/7378726?hl=en) to learn how to create such an account.
Then, check out section ***For Bots: Using Service Account*** on this [gspread documentation page](https://docs.gspread.org/en/v6.1.3/oauth2.html#for-bots-using-service-account) in order to properly place JSON with the credentials. Also, make sure to share access to the spreadsheet with the service account in case the document is not openly accessible. 

*diffconfig* and *extract-ikconfig* are the scripts provided by the Linux kernel to conveniently extract and diff kernel configs. Taken from [here](https://github.com/torvalds/linux/tree/master/scripts). Make sure they are executable with chmod +x. 

In order to dump comparison info to a Google spreadsheet:
```
python3 dump_to_sheets.py <spreadsheet name> <vendor folder 1> <vendor folder 2> ...
```
Make sure the vendor folder names match the case.

The resulting spreadsheet will contain the firmware codename, kernel version, Android version, an indication whether the kernel exactly matches the GKI counterpart (Y/N). The next 7 columns concern extracted kernel symbols. In the context of the comparison between a vendor kernel and a GKI kernel, one can look at the list of symbols present/absent for the pair of kernels. Thus, 3 numbers separated by "/" mean the amount of symbols unique to the OEM's kernel, the amount of symbols unique to the corresponding GKI kernel, and the symbols that have the exact name match for both kernels. The exact symbol name match is the trickiest part, because vendors may 
build their kernels with slightly modified toolchains and/or different flags. Thus, some symbols may get duplicated, or get some postfixes appended, etc. So the next 7 columns addresses matching symbols in such cases. The comparison is performed in rounds, such that the columns mean the following:
 - "initial" refers to the original count of matching and unique symbols;
 - "numbers" means treating "symbol_name" and "symbol_name.1234" as the same symbol, so unique and common symbols get recounted;
 - ".cfi_jt" in the next round means additionally treating "symbol_name" and "symbol_name.cfi_jt" as the same symbol;
 - "numbers 2" round is used to handle cases like "symbol_name.1234.cfi_jt.1234";
 - "(.llvm, .__key, .__msg)" additionally collapses symbols with these postfixes;
 - "(global-local collapse)" means treating "T symbol_name" and "t symbol_name" as the same symbol;
 - "no sym types" round means ignoring all symbol types specified before the symbol name.

After the final symbol comparison round, there is a column titled ".config +/-/modif". It reflects the comparison between the two exatracted kernel build configs. The colum name stands for added, deleted and modified config lines in the vendor kernel as compared to the counterpart GKI.

After this comparison round, what is left to fill out are the columns about the consumer model name, chipset and release date, which is the next step.

## 3. Retrieve phone model info
**model_info_vpn.py** scrapes GSMArena for the phone models that use given firmware. To prevent being detected, the script uses rotating VPNs. In this particular case, Mullvad VPN with Wireguard were used, so the script expects a *mullvad* folder containing valid VPN configs. Information for the tool setup is [here](https://mullvad.net/en/help/easy-wireguard-mullvad-setup-linux).

Please place the Mullvad configs in the expected directory:

``` 
├── diffconfig
├── dump_to_sheets.py
├── pull_kernels.py
├── gki_scrape.py
├── syms_helpers.py
├── model_info_vpn.py
├── extract-ikconfig
├── mullvad
│   ├── dk-cph-wg-001.conf
│   └── dk-cph-wg-002.conf
├── README.md
├── samsung/
├── redmi/
├── ...
└── requirements.txt
```

Run with 
```
python3 model_info_vpn.py <spreadsheet name>
```

As a result, the existing table of symbols will now be complete with phone model information.

# Source code statistics
The following scripts allow to aggregate some statistics regarding kernel source code modifications. The idea is to compare vendor kernel source code and the corresponding AOSP kernel source. Some information on where to look for source code:
 - AOSP kernel source resides [here](https://android.googlesource.com/kernel/common/).
 - For Samsung, a [dedicated website](https://opensource.samsung.com/uploadList?menuItem=mobile) provides source code on per-model basis. The downside is that it is always packaged as a .zip file, and the download speed is really bad.
 - For Xiaomi/Redmi, there is a [dedicated GitHub repository](https://github.com/MiCode/Xiaomi_Kernel_OpenSource).
 - For Oppo, kernel source code can be found on [GitHub](https://github.com/oppo-source). One thing to keep in mind is that the provided code is not per particular phone model, but per particular chipset.
 - For Vivo, there is also a [dedicated website](https://opensource.vivo.com/Project). The codebases here are a mix of per-chipset and per-model.

One of the scripts expects two environment variables to be set, one of those points to the directory with GKI source code, and the other one points to the vendor source.
```
export GKI=/path/to/gki/source
export VENDOR=/path/to/vendor/source
```
Also, it is important to create a directory with initialized git for source code comparison. There, the corresponding codebases will be copied to their own branches, and *git diff* will be used for comparison. Please set the variable COMPARE_SOURCES_DIR in compare_sources.py accordingly. 

In order to run the script, do: 
```
python3 compare_sources.py <gki_branch_name> <vendor_branch_name> <output folder path>
```
Please create output folder beforehand.

For every codebase of interest, the script will generate 4 files in the output folder:
 - <vendor_branch_name>.txt, which is the output of *git diff* for two branches.
 - <vendor_branch_name>_code.txt, which is the output of *git diff* for two branches, but only for files that are code (the list of selected file formats can be seen in the script code)
 - <vendor_branch_name>_aggregated.json, which is a JSON representation of the <vendor_branch_name>.txt
 - <vendor_branch_name>_aggregated_code.json, which is a JSON representation of the <vendor_branch_name>_code.txt

 The JSON representations of the diff shows nested diff, aggregating the added and deleted modifications according to the directory structure. To conventiently see and compare the diffs, use *side_by_side.html*.

Now, after dumping code diffs of many vendor models, we can aggregate these statistics as well. *vendor_code_stat.py* expects a folder with <vendor_branch_name>_aggregated_code.json files. This script averages the amount of modifications per given top-level directory in kernel code structure, and writes this info to a .json file. Usage:

```
python3 vendor_code_stat.py <json directory> <output_file_path.json>
```

To visualize this aggregated data from the previously mentioned output_file_path.json, use bar_charts.py:

```
python3 bar_charts.py <output_file_path.json> <x label>
```

# Future work/enhancements
The analysis applied can/should be expanded with more ways to assess both kernels and the source code.
For the kernels, the spreadsheet can be expanded to include, for example, whether certain kernel security configs are present/enabled compared to their GKI counterparts; or any other relevant security metrics. It is also important to note that the symbol name similarity is not necessarily a comprehensive metric, as it does not reflect the fact that even identically named symbols may contain custom modifications.

The codebase part is rather interesting. The vendors only publish the kernel source code due to GPLv2 obligations. Otherwise, OEMs naturally would wish to keep their code private to themselves. And though they are obliged to release the kernel code, there are certain circumstances or simply licensing caveats/tricks that allow to [keep certain modules private](https://unix.stackexchange.com/questions/13284/proprietary-or-closed-parts-of-the-kernel). Thus, "we don't know what we don't know". A very interesting read on proprietary modules and ways to circumvent licansing limitations can be found [here](https://lwn.net/Articles/939842/?utm_source=chatgpt.com).

If the goal is to specifically identify closed-source modules, the suggested step would be to try to map .ko modules from a firmware package to the published source by examining build configurations/Makefiles. Another approach, perhaps a bit more tedious, could be searching for symbols that are present in the binary, but not present in the source code. One could also look for .bin binary blobs, that are not covered by the GPL licence. 

# Related work 
## Fragmentation impact 
Here are some papers that conducted analysis across different parts of the Android firmware stack (mostly userspace). These works point out how much security risk can be introduced by custom modifications.

[1] Y. Ji, M. Elsabagh, R. Johnson, and A. Stavrou. DEFInit: An analysis of exposed android init routines. In 30th USENIX Security Symposium (USENIX Security 21), pages 3685–3702. USENIX Association, Aug. 2021.

[2] M. Elsabagh, R. Johnson, A. Stavrou, C. Zuo, Q. Zhao, and Z. Lin. FIRMSCOPE: Automatic uncovering of Privilege-Escalation vulnerabilities in Pre-Installed apps in android firmware. In 29th USENIX Security Symposium (USENIX Security 20), pages 2379–2396. USENIX Association, Aug. 2020.

[3] L. Wu, M. Grace, Y. Zhou, C. Wu, and X. Jiang. The impact of vendor customizations on android security. In Proceedings of the 2013 ACM SIGSAC Conference on Computer & Communications Security, CCS ’13, page 623–634, New York, NY, USA, 2013. Association for Computing Machinery.

[4] L. Maar, F. Draschbacher, L. Lamster, and S. Mangard. Defects-in-Depth: Analyzing the integration of effective defenses against
One-Day exploits in android kernels. In 33rd USENIX Security Symposium (USENIX Security 24), pages 4517–4534, Philadelphia, PA, Aug. 2024. USENIX Association.

[5] M. Busch, P. Mao, and M. Payer. Spill the TeA: An empirical study of trusted application rollback prevention on android smartphones. In 33rd USENIX Security Symposium (USENIX Security 24), pages 5071–5088, Philadelphia, PA, Aug. 2024. USENIX Association.

[6] Z. El-Rewini and Y. Aafer. Dissecting residual apis in custom android roms. In Proceedings of the 2021 ACM SIGSAC Conference on
Computer and Communications Security, CCS ’21, page 1598–1611, New York, NY, USA, 2021. Association for Computing Machinery.

[7] Andrea Possemato, Simone Aonzo, Davide Balzarotti, Yanick Fratantonio. Trust, But Verify: A Longitudinal Analysis Of Android OEM
Compliance and Customization. SP 2021, IEEE Symposium on Security and Privacy, IEEE, May 2021, San Francisco, United States. pp.87-102, 10.1109/SP40001.2021.00074. hal-04611606

[8] Q. Hou, W. Diao, Y. Wang, X. Liu, S. Liu, L. Ying, S. Guo, Y. Li, M. Nie, and H. Duan. Large-scale security measurements on the android firmware ecosystem. In Proceedings of the 44th International Conference on Software Engineering, ICSE ’22, page 1257–1268, New York, NY, USA, 2022. Association for Computing Machinery.

## Rehosting
Rehosting papers are relevant for understanding how to approach dynamic analysis of Android images. Once the fragmentation image points out how the changes are structured in the system, it defines which components are the highest priority for emulation, and this impacts the exact technical steps.

[9] D. D. Chen, M. Egele, M. Woo, and D. Brumley, “Towards Automated Dynamic Analysis for Linux-based Embedded Firmware,” in Proceedings of the Network and Distributed System Security Symposium (NDSS), 2016.

[10] Prashast Srivastava, Hui Peng, Jiahao Li, Hamed Okhravi, Howard Shrobe, and Mathias Payer. Firmfuzz: Automated iot firmware introspection and analysis. In Proceedings of the 2nd International ACM Workshop on Security and Privacy for the Internet-of-Things, pages 15–21, 2019.

[11] Mingeun Kim, Dongkwan Kim, Eunsoo Kim, Suryeon Kim, Yeongjin Jang, and Yongdae Kim. Firmae: Towards large-scale emulation of iot firmware for dynamic analysis. In Annual Computer Security Applications Conference (ACSAC), 2020.

[12] I. Angelakopoulos, G. Stringhini, and M. Egele, “FirmSolo: Enabling dynamic analysis of binary Linux-based IoT kernel modules,” in Proceedings of the USENIX Security Symposium, 2023

[13] I. Pustogarov, Q. Wu and D. Lie, "Ex-vivo dynamic analysis framework for Android device drivers," 2020 IEEE Symposium on Security and Privacy (SP), San Francisco, CA, USA, 2020, pp. 1088-1105, doi: 10.1109/SP40000.2020.00094.




