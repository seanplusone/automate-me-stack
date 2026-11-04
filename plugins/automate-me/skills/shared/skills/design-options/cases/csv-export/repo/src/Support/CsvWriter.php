<?php

// Streams rows to the browser as a CSV download, one row at a time.
class CsvWriter
{
    private $out;

    public static function download($filename, array $headers)
    {
        header('Content-Type: text/csv');
        header('Content-Disposition: attachment; filename="' . $filename . '"');
        $writer = new self(fopen('php://output', 'w'));
        $writer->row($headers);
        return $writer;
    }

    public function __construct($handle)
    {
        $this->out = $handle;
    }

    public function row(array $cells)
    {
        fputcsv($this->out, $cells);
    }
}
