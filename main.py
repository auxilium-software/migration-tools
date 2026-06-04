from runners.auxilium_1_to_3.step_0_file_decryption import Step0FileDecryption
from runners.auxilium_1_to_3.step_1_db_dump import Step1DbDump
from runners.auxilium_1_to_3.step_2_index import Step2Index
from runners.auxilium_1_to_3.step_9_data_upload import Step9DataUpload


def aux_1_to_3_go() -> None:
    print("S0: file decryption")
    Step0FileDecryption().go()

    print("S1: database dump")
    Step1DbDump().go()

    print("S2: index")
    Step2Index().go()

    print("S9: data upload")
    Step9DataUpload().go()




def main() -> None:
    aux_1_to_3_go()


if __name__ == "__main__":
    main()
