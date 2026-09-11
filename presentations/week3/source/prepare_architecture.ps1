# Convert SVG text to vector paths with the installed Korean font.
# Keep the editable SVG as source; embed the outlined copy for portable rendering.
Add-Type -AssemblyName System.Drawing
$ns = 'http://www.w3.org/2000/svg'
[xml]$doc = Get-Content -LiteralPath (Join-Path $PSScriptRoot '보안RAG_전체구조_발표용.svg') -Raw
$family = [System.Drawing.FontFamily]::new('Malgun Gothic')
$format = [System.Drawing.StringFormat]::GenericTypographic.Clone()
$format.FormatFlags = $format.FormatFlags -bor [System.Drawing.StringFormatFlags]::NoWrap
$culture = [System.Globalization.CultureInfo]::InvariantCulture
function Num($v) { $v.ToString('0.###', $culture) }
foreach ($element in @($doc.SelectNodes('//*[local-name()="text"]'))) {
    $size = [single]::Parse($element.GetAttribute('font-size'), $culture)
    $style = [System.Drawing.FontStyle]::Regular
    if ($element.GetAttribute('font-weight') -eq '700') { $style = [System.Drawing.FontStyle]::Bold }
    $x = [single]::Parse($element.GetAttribute('x'), $culture)
    $baseline = [single]::Parse($element.GetAttribute('y'), $culture)
    $ascent = $size * $family.GetCellAscent($style) / $family.GetEmHeight($style)
    $glyphPath = [System.Drawing.Drawing2D.GraphicsPath]::new()
    $glyphPath.AddString($element.InnerText, $family, [int]$style, $size, [System.Drawing.PointF]::new($x, $baseline - $ascent), $format)
    $points = $glyphPath.PathPoints
    $types = $glyphPath.PathTypes
    $commands = [System.Collections.Generic.List[string]]::new()
    for ($i = 0; $i -lt $points.Length; $i++) {
        $kind = $types[$i] -band 7
        if ($kind -eq 0) { $commands.Add("M $(Num $points[$i].X) $(Num $points[$i].Y)") }
        elseif ($kind -eq 1) { $commands.Add("L $(Num $points[$i].X) $(Num $points[$i].Y)") }
        elseif ($kind -eq 3) {
            $commands.Add("C $(Num $points[$i].X) $(Num $points[$i].Y) $(Num $points[$i+1].X) $(Num $points[$i+1].Y) $(Num $points[$i+2].X) $(Num $points[$i+2].Y)")
            $i += 2
        }
        if (($types[$i] -band 128) -ne 0) { $commands.Add('Z') }
    }
    $path = $doc.CreateElement('path', $ns)
    $path.SetAttribute('d', ($commands -join ' '))
    $path.SetAttribute('fill', $element.GetAttribute('fill'))
    $path.SetAttribute('aria-label', $element.InnerText)
    [void]$element.ParentNode.ReplaceChild($path, $element)
    $glyphPath.Dispose()
}
foreach ($line in @($doc.SelectNodes('//*[local-name()="line"][@marker-end]'))) {
    $x = [double]$line.GetAttribute('x2'); $y = [double]$line.GetAttribute('y2')
    $arrow = $doc.CreateElement('path', $ns)
    $arrow.SetAttribute('d', "M $($x-5) $($y-8) L $($x+5) $($y-8) L $x $y Z")
    $arrow.SetAttribute('fill', $line.GetAttribute('stroke'))
    [void]$line.ParentNode.AppendChild($arrow)
    $line.RemoveAttribute('marker-end')
}
$arrow = $doc.CreateElement('path', $ns)
$arrow.SetAttribute('d', 'M 800 617 L 808 622 L 800 627 Z')
$arrow.SetAttribute('fill', '#38bdf8')
[void]$doc.DocumentElement.AppendChild($arrow)
$doc.Save((Join-Path $PSScriptRoot '보안RAG_전체구조_글꼴윤곽.svg'))
$format.Dispose(); $family.Dispose()
Write-Output 'Prepared portable SVG'
