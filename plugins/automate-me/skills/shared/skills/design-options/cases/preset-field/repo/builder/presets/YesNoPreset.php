<?php

class YesNoPreset extends Preset
{
    public static $label = 'Yes / No';
    public static $baseField = SelectField::class;

    public static function settings()
    {
        return ['options' => ['yes' => 'Yes', 'no' => 'No']];
    }
}
