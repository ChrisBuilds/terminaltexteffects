import utils.terminaloperations as tops
from effects import expand, pour, random_sequence, scattered, sparkler, rain


test_data = """!This
    is
        test
            data.@
    """


def main():
    input_data = tops.get_piped_input()
    if not input_data:
        input_data = "No input data."
    # input_data = test_data
    tte_effect = pour.PouringEffect(input_data, pour.PourDirection.DOWN)
    # tte_effect = scattered.ScatteredEffect(input_data)
    # tte_effect = expand.ExpandEffect(input_data)
    # tte_effect = random_sequence.RandomSequence(input_data)
    # tte_effect = sparkler.SparklerEffect(input_data, sparkler.SparklerPosition.SE)
    # tte_effect = rain.RainEffect(input_data)
    tte_effect.run(rate=0.01)


if __name__ == "__main__":
    main()
