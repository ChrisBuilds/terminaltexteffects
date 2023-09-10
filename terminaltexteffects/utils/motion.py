import typing

if typing.TYPE_CHECKING:
    from terminaltexteffects import base_character


class Motion:
    def __init__(self, character: "base_character.EffectCharacter"):
        self.character = character

    def move(self) -> None:
        """Moves the character one step closer to the target position based on speed and acceleration."""
        self.character.previous_coord.column, self.character.previous_coord.row = (
            self.character.current_coord.column,
            self.character.current_coord.row,
        )
        # set the origin coordinate to the current coordinate if the origin has not been otherwise set
        if (
            self.character.origin.column == self.character.input_coord.column
            and self.character.origin.row == self.character.input_coord.row
        ):
            self.character.origin.column, self.character.origin.row = (
                self.character.current_coord.column,
                self.character.current_coord.row,
            )
        self.character.speed.accelerate()

        # if the character has reached the target coordinate, pop the next coordinate from the waypoints list
        # and reset the move_delta for recalculation
        if self.character.current_coord == self.character.target_coord and self.character.waypoints:
            self.character.target_coord = self.character.waypoints.pop(0)
            self.character.origin.column, self.character.origin.row = (
                self.character.current_coord.column,
                self.character.current_coord.row,
            )
            self.character.move_delta = 0

        column_distance = abs(self.character.current_coord.column - self.character.target_coord.column)
        row_distance = abs(self.character.current_coord.row - self.character.target_coord.row)
        # on first call, calculate the column and row movement distance to approximate an angled line
        if not self.character.move_delta:
            self.character.tweened_column = self.character.current_coord.column
            self.character.tweened_row = self.character.current_coord.row
            self.character.move_delta = min(column_distance, row_distance) / max(column_distance, row_distance, 1)
            if self.character.move_delta == 0:
                self.character.move_delta = 1

            if column_distance < row_distance:
                self.character.column_delta = self.character.move_delta
                self.character.row_delta = 1
            elif row_distance < column_distance:
                self.character.row_delta = self.character.move_delta
                self.character.column_delta = 1
            else:
                self.character.column_delta = self.character.row_delta = 1
        # if the speed is high enough to jump over the target coordinate, set the current coordinate to the target coordinate
        if (
            abs(self.character.current_coord.column - self.character.target_coord.column)
            < self.character.column_delta * self.character.speed.current
        ):
            self.character.current_coord.column = self.character.target_coord.column
        if (
            abs(self.character.current_coord.row - self.character.target_coord.row)
            < self.character.row_delta * self.character.speed.current
        ):
            self.character.current_coord.row = self.character.target_coord.row
        # adjust the column and row positions by the calculated delta, round down to int
        if self.character.current_coord.column < self.character.target_coord.column:
            self.character.tweened_column += self.character.column_delta * self.character.speed.current
            self.character.current_coord.column = int(self.character.tweened_column)
        elif self.character.current_coord.column > self.character.target_coord.column:
            self.character.tweened_column -= self.character.column_delta * self.character.speed.current
            self.character.current_coord.column = int(self.character.tweened_column)
        if self.character.current_coord.row < self.character.target_coord.row:
            self.character.tweened_row += self.character.row_delta * self.character.speed.current
            self.character.current_coord.row = int(self.character.tweened_row)
        elif self.character.current_coord.row > self.character.target_coord.row:
            self.character.tweened_row -= self.character.row_delta * self.character.speed.current
            self.character.current_coord.row = int(self.character.tweened_row)
