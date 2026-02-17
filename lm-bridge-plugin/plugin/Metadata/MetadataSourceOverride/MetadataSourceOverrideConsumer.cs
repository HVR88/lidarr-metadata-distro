using FluentValidation.Results;
using NzbDrone.Core.Extras.Metadata;
using NzbDrone.Core.Extras.Metadata.Files;
using NzbDrone.Core.MediaFiles;
using NzbDrone.Core.Music;
using NzbDrone.Core.ThingiProvider;

namespace LMBridgePlugin.Metadata.MetadataSourceOverride
{
    public class MetadataSourceOverrideConsumer : IMetadata
    {
        public const string DisplayName = "LM Bridge Settings";
        public string Name => DisplayName;
        public Type ConfigContract => typeof(MetadataSourceOverrideSettings);
        public ProviderMessage? Message => null;
        public IEnumerable<ProviderDefinition> DefaultDefinitions => [];
        public ProviderDefinition? Definition { get; set; }

        public object RequestAction(string action, IDictionary<string, string> query) => default!;

        public ValidationResult Test() => new();

        public string GetFilenameAfterMove(Artist artist, TrackFile trackFile, MetadataFile metadataFile) =>
            Path.ChangeExtension(trackFile.Path, Path.GetExtension(Path.Combine(artist.Path, metadataFile.RelativePath)).TrimStart('.'));

        public string GetFilenameAfterMove(Artist artist, string albumPath, MetadataFile metadataFile) =>
            Path.Combine(artist.Path, albumPath, Path.GetFileName(metadataFile.RelativePath));

        public MetadataFile FindMetadataFile(Artist artist, string path) => default!;

        public MetadataFileResult ArtistMetadata(Artist artist) => default!;

        public MetadataFileResult AlbumMetadata(Artist artist, Album album, string albumPath) => default!;

        public MetadataFileResult TrackMetadata(Artist artist, TrackFile trackFile) => default!;

        public List<ImageFileResult> ArtistImages(Artist artist) => [];

        public List<ImageFileResult> AlbumImages(Artist artist, Album album, string albumPath) => [];

        public List<ImageFileResult> TrackImages(Artist artist, TrackFile trackFile) => [];

        public override string ToString() => Name;
    }
}
