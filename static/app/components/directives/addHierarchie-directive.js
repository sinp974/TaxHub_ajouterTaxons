app.directive('addHierarchieDir', ['$http', 'backendCfg', function ($http, backendCfg) {
  return {
    restrict: 'AE',
    templateUrl:'static/app/components/directives/addHierarchie-template.html',
    scope : {
      taxHierarchieSelected:'=',
      searchUrl:'@',
    },
    link:function($scope, $element, $attrs) {
      //Initialisation
      $scope.$watch('taxHierarchieSelected', function(newVal, oldVal) {
        if ($scope.taxHierarchieSelected) {
          if ($scope.taxHierarchieSelected.regne)
            $scope.regne = {'regne': $scope.taxHierarchieSelected.regne, 'nb_tx_kd': $scope.taxHierarchieSelected.nb_tx_kd };
          else $scope.regne = undefined;

          if ($scope.taxHierarchieSelected.phylum)
            $scope.phylum = {'phylum': $scope.taxHierarchieSelected.phylum, 'nb_tx_ph': $scope.taxHierarchieSelected.nb_tx_ph };
          else $scope.phylum = undefined;

          if ($scope.taxHierarchieSelected.classe)
            $scope.classe = {'classe': $scope.taxHierarchieSelected.classe, 'nb_tx_cl': $scope.taxHierarchieSelected.nb_tx_cl };
          else $scope.classe = undefined;

          if ($scope.taxHierarchieSelected.ordre)
            $scope.ordre = {'ordre': $scope.taxHierarchieSelected.ordre, 'nb_tx_or': $scope.taxHierarchieSelected.nb_tx_or };
          else $scope.ordre = undefined;

          if ($scope.taxHierarchieSelected.famille)
            $scope.famille = {'famille': $scope.taxHierarchieSelected.famille, 'nb_tx_fm': $scope.taxHierarchieSelected.nb_tx_fm };
          else $scope.famille = undefined;

          if ($scope.taxHierarchieSelected.sous_famille)
            $scope.sous_famille = {'sous_famille': $scope.taxHierarchieSelected.sous_famille, 'nb_tx_sbfm': $scope.taxHierarchieSelected.nb_tx_sbfm };
          else $scope.sous_famille = undefined;

          if ($scope.taxHierarchieSelected.tribu)
            $scope.tribu = {'tribu': $scope.taxHierarchieSelected.tribu, 'nb_tx_tr': $scope.taxHierarchieSelected.nb_tx_tr };
          else $scope.tribu = undefined;
        }
      }, true);

      $scope.onSelect = function ($item, $model, $label) {
        $scope.$item = $item;
        $scope.$model = $model;
        $scope.$label = $label;
        this.taxHierarchieSelected = $item;
      };

      $scope.getTaxonHierarchie = function(rang, val, model) {
        var queryparam = {params : {'ilike': val.trim()}} ;
        if (model) {
            if ((model.regne) && (rang !=='KD'))
              queryparam.params.regne = model.regne.trim();

            if ((model.phylum) && ((rang !=='PH') && (rang !=='KD')))
              queryparam.params.phylum = model.phylum.trim();

            if ((model.classe) && ((rang !=='CL') && (rang !=='PH') && (rang !=='KD')))
              queryparam.params.classe = model.classe.trim();

            if ((model.ordre) && ((rang !=='OR') && (rang !=='CL') && (rang !=='PH') && (rang !=='KD')))
              queryparam.params.ordre = model.ordre.trim();

            if ((model.famille) && ((rang !=='FM') && (rang !=='OR') && (rang !=='CL') && (rang !=='PH') && (rang !=='KD')))
              queryparam.params.famille = model.famille.trim();

            if ((model.sous_famille) && ((rang !=='SBFM') && (rang !=='FM') && (rang !=='OR') && (rang !=='CL') && (rang !=='PH') && (rang !=='KD')))
              queryparam.params.sous_famille = model.sous_famille.trim();
        }
        return $http.get(backendCfg.api_url+this.searchUrl+rang, queryparam).then(function(response){
          return response.data;
        });
      };

      // Vider la sélection des rang taxonomiques 
      $scope.refreshForm = function() {
        // if (($scope.taxHierarchieSelected === undefined) || ($scope.taxHierarchieSelected === '=')) {
        if ($scope.taxHierarchieSelected === undefined) {
          alert("La hiérarchie taxonomique est déjà vide.");
        } else {
          $scope.resetTaxHierarchy();
        }
      };

      $scope.resetTaxHierarchy = function() {
        $scope.taxHierarchieSelected = undefined;
        $scope.regne = undefined;
        $scope.phylum = undefined;
        $scope.classe = undefined;
        $scope.ordre = undefined;
        $scope.famille = undefined;
        $scope.sous_famille = undefined;
        $scope.tribu = undefined;
      };

      // Écouter l'événement de réinitialisation : fait le lien entre le controler et la directive
      $scope.$on('resetTaxHierarchy', function() {
        $scope.resetTaxHierarchy();
      });

    }
  }
}]);
